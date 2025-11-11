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
    logger.debug("Checking for due board templates...")

    # Get database session
    async for session in get_db():
        try:
            # Query for due templates
            result = await session.execute(
                select(BoardTemplateORM).where(
                    BoardTemplateORM.is_active.is_(True),
                    BoardTemplateORM.next_run_at <= datetime.now(UTC),
                    BoardTemplateORM.deleted_at.is_(None),
                )
            )
            due_templates = result.scalars().all()

            if not due_templates:
                logger.debug("No due templates found")
                return

            logger.info("Found %d due templates to process", len(due_templates))

            # Process each template
            board_service = BoardService(session)
            template_service = BoardTemplateService(session)

            for template_orm in due_templates:
                try:
                    template = template_orm.to_domain()

                    # Generate unique short code
                    short_code = await generate_unique_short_code(session)

                    # Calculate board time range
                    starts_at = template.next_run_at
                    # Parse interval and add to starts_at for ends_at
                    # For now, we'll use a simple approach - could be enhanced later
                    from datetime import timedelta

                    # Extract days from repeat_interval (e.g., "7 days" -> 7)
                    # This is a simple parser - could be made more robust
                    interval_parts = template.repeat_interval.split()
                    if len(interval_parts) >= 2:
                        amount = int(interval_parts[0])
                        unit = interval_parts[1].lower().rstrip("s")  # Remove trailing 's'

                        if unit == "day":
                            ends_at = starts_at + timedelta(days=amount)
                        elif unit == "week":
                            ends_at = starts_at + timedelta(weeks=amount)
                        elif unit == "hour":
                            ends_at = starts_at + timedelta(hours=amount)
                        elif unit == "minute":
                            ends_at = starts_at + timedelta(minutes=amount)
                        else:
                            # Default to same duration as interval suggests
                            ends_at = starts_at + timedelta(days=amount)
                    else:
                        # Fallback: no end date
                        ends_at = None

                    # Extract board config from template
                    icon = template.config.get("icon", "trophy")
                    unit = template.config.get("unit", "points")
                    is_active = template.config.get("is_active", True)
                    sort_direction = template.config.get("sort_direction", "desc")
                    keep_strategy = template.config.get("keep_strategy", "best")
                    tags = template.config.get("tags", [])

                    # Create board using service
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
                        tags=tags if isinstance(tags, list) else [],
                    )

                    # Update template's next_run_at
                    # Parse interval again and add to next_run_at
                    if unit == "day":
                        next_run = template.next_run_at + timedelta(days=amount)
                    elif unit == "week":
                        next_run = template.next_run_at + timedelta(weeks=amount)
                    elif unit == "hour":
                        next_run = template.next_run_at + timedelta(hours=amount)
                    elif unit == "minute":
                        next_run = template.next_run_at + timedelta(minutes=amount)
                    else:
                        next_run = template.next_run_at + timedelta(days=amount)

                    await template_service.update_board_template(
                        template_id=template.id,
                        next_run_at=next_run,
                    )

                    logger.info(
                        "Created board '%s' from template %s, next run at %s",
                        template.name,
                        template.id,
                        next_run,
                    )

                except Exception:
                    logger.exception("Failed to process template %s", template_orm.id)
                    # Continue with next template
                    continue

            await session.commit()
            logger.info("Successfully processed %d templates", len(due_templates))

        except Exception:
            logger.exception("Error in process_due_templates")
            await session.rollback()


async def expire_boards() -> None:
    """Expire boards that have passed their end date.

    Queries for active boards where ends_at <= now() and sets is_active=False.

    This task is designed to be called periodically (e.g., every minute).
    """
    logger.debug("Checking for expired boards...")

    # Get database session
    async for session in get_db():
        try:
            # Query for expired boards
            result = await session.execute(
                select(BoardORM).where(
                    BoardORM.ends_at <= datetime.now(UTC),
                    BoardORM.ends_at.is_not(None),
                    BoardORM.is_active.is_(True),
                    BoardORM.deleted_at.is_(None),
                )
            )
            expired_boards = result.scalars().all()

            if not expired_boards:
                logger.debug("No expired boards found")
                return

            logger.info("Found %d expired boards", len(expired_boards))

            # Expire each board
            for board_orm in expired_boards:
                board_orm.is_active = False
                board_orm.updated_at = datetime.now(UTC)

            await session.commit()
            logger.info("Successfully expired %d boards", len(expired_boards))

        except Exception:
            logger.exception("Error in expire_boards")
            await session.rollback()
