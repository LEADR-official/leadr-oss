"""Background tasks for board processing.

Contains tasks for:
- Processing due board templates and creating boards
- Expiring boards past their end date
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select

from leadr.boards.adapters.orm import BoardORM, BoardTemplateORM
from leadr.boards.services.board_service import BoardService
from leadr.boards.services.board_template_service import BoardTemplateService
from leadr.boards.services.short_code_generator import generate_unique_short_code
from leadr.common.database import get_db

logger = logging.getLogger(__name__)


async def process_due_templates() -> None:
    """Process all due board templates and create boards.

    Queries for active templates where next_run_at <= now(), creates boards
    from each template, and updates the template's next_run_at.

    This task is designed to be called periodically (e.g., every minute).
    """
    from datetime import timedelta

    from sqlalchemy.exc import DBAPIError, OperationalError

    logger.debug("Checking for due board templates...")

    # Get database session
    async for session in get_db():
        # Query for due templates - fail fast on database errors
        try:
            result = await session.execute(
                select(BoardTemplateORM).where(
                    BoardTemplateORM.is_active.is_(True),
                    BoardTemplateORM.next_run_at <= datetime.now(UTC),
                    BoardTemplateORM.deleted_at.is_(None),
                )
            )
            due_templates = result.scalars().all()
        except (OperationalError, DBAPIError) as e:
            logger.error("Database error querying templates: %s", e)
            return

        if not due_templates:
            logger.debug("No due templates found")
            return

        logger.info("Found %d due templates to process", len(due_templates))

        # Process each template individually
        board_service = BoardService(session)
        template_service = BoardTemplateService(session)
        success_count = 0

        for template_orm in due_templates:
            # Convert to domain model - skip on error
            try:
                template = template_orm.to_domain()
            except Exception:
                logger.exception("Failed to convert template %s to domain", template_orm.id)
                continue

            # Generate unique short code - skip template on failure
            try:
                short_code = await generate_unique_short_code(session)
            except RuntimeError:
                logger.exception(
                    "Failed to generate unique short code for template %s", template.id
                )
                continue

            # Parse interval and calculate time range - skip on parse error
            try:
                starts_at = template.next_run_at
                interval_parts = template.repeat_interval.split()

                if len(interval_parts) >= 2:
                    amount = int(interval_parts[0])
                    unit = interval_parts[1].lower().rstrip("s")

                    if unit == "day":
                        duration = timedelta(days=amount)
                    elif unit == "week":
                        duration = timedelta(weeks=amount)
                    elif unit == "hour":
                        duration = timedelta(hours=amount)
                    elif unit == "minute":
                        duration = timedelta(minutes=amount)
                    else:
                        duration = timedelta(days=amount)

                    ends_at = starts_at + duration
                    next_run = template.next_run_at + duration
                else:
                    # Invalid interval format
                    logger.error(
                        "Invalid repeat_interval format for template %s: %s",
                        template.id,
                        template.repeat_interval,
                    )
                    continue
            except (ValueError, IndexError):
                logger.exception(
                    "Failed to parse repeat_interval for template %s: %s",
                    template.id,
                    template.repeat_interval,
                )
                continue

            # Extract board config - use defaults on missing/invalid values
            icon = template.config.get("icon", "trophy")
            unit = template.config.get("unit", "points")
            is_active = template.config.get("is_active", True)
            sort_direction = template.config.get("sort_direction", "desc")
            keep_strategy = template.config.get("keep_strategy", "best")
            tags = template.config.get("tags", [])
            if not isinstance(tags, list):
                tags = []

            # Create board - skip template on failure
            try:
                await board_service.create_board(
                    account_id=template.account_id,
                    game_id=template.game_id,
                    name=template.name,
                    icon=icon,
                    short_code=short_code,
                    unit=unit,
                    is_active=is_active,
                    sort_direction=sort_direction,
                    keep_strategy=keep_strategy,
                    template_id=template.id,
                    template_name=template.name,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    tags=tags,
                )
            except ValueError:
                logger.exception("Validation error creating board from template %s", template.id)
                continue
            except Exception:
                logger.exception("Failed to create board from template %s", template.id)
                continue

            # Update template's next_run_at - skip on failure
            try:
                await template_service.update_board_template(
                    template_id=template.id,
                    next_run_at=next_run,
                )
            except Exception:
                logger.exception("Failed to update next_run_at for template %s", template.id)
                continue

            success_count += 1
            logger.info(
                "Created board '%s' from template %s, next run at %s",
                template.name,
                template.id,
                next_run,
            )

        # Commit all successful template processing - fail fast on commit error
        try:
            await session.commit()
            logger.info("Successfully processed %d/%d templates", success_count, len(due_templates))
        except (OperationalError, DBAPIError) as e:
            logger.error("Database error committing template results: %s", e)
            await session.rollback()


async def expire_boards() -> None:
    """Expire boards that have passed their end date.

    Queries for active boards where ends_at <= now() and sets is_active=False.

    This task is designed to be called periodically (e.g., every minute).
    """
    from sqlalchemy.exc import DBAPIError, OperationalError

    logger.debug("Checking for expired boards...")

    # Get database session
    async for session in get_db():
        # Query for expired boards - fail fast on database errors
        try:
            result = await session.execute(
                select(BoardORM).where(
                    BoardORM.ends_at <= datetime.now(UTC),
                    BoardORM.ends_at.is_not(None),
                    BoardORM.is_active.is_(True),
                    BoardORM.deleted_at.is_(None),
                )
            )
            expired_boards = result.scalars().all()
        except (OperationalError, DBAPIError) as e:
            logger.error("Database error querying expired boards: %s", e)
            return

        if not expired_boards:
            logger.debug("No expired boards found")
            return

        logger.info("Found %d expired boards", len(expired_boards))

        # Expire each board
        now = datetime.now(UTC)
        for board_orm in expired_boards:
            board_orm.is_active = False
            board_orm.updated_at = now

        # Commit changes - fail fast on commit error
        try:
            await session.commit()
            logger.info("Successfully expired %d boards", len(expired_boards))
        except (OperationalError, DBAPIError) as e:
            logger.error("Database error committing board expiry: %s", e)
            await session.rollback()
