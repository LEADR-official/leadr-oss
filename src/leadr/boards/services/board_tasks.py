"""Background tasks for board processing.

Contains tasks for:
- Processing due board templates and creating boards
- Expiring boards past their end date
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, OperationalError

from leadr.boards.adapters.orm import BoardORM, BoardTemplateORM
from leadr.boards.services.board_service import BoardService
from leadr.boards.services.board_template_service import BoardTemplateService
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

            # Create board from template - skip on any error
            # (short_code is generated automatically by the service)
            try:
                board = await board_service.create_board_from_template(template)
            except ValueError:
                logger.exception("Validation error creating board from template %s", template.id)
                continue
            except RuntimeError:
                logger.exception("Failed to generate short code for template %s", template.id)
                continue
            except Exception:
                logger.exception("Failed to create board from template %s", template.id)
                continue

            # Advance template schedule - skip on failure
            try:
                updated_template = await template_service.advance_template_schedule(template.id)
            except Exception:
                logger.exception("Failed to advance schedule for template %s", template.id)
                continue

            success_count += 1
            logger.info(
                "Created board '%s' from template %s, next run at %s",
                board.name,
                template.id,
                updated_template.next_run_at,
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
