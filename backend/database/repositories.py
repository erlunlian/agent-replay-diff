from uuid import UUID
from uuid import UUID as UUID_t

from domain.models import Run as RunDom
from domain.models import Span as SpanDom
from domain.models import User as UserDom
from sqlmodel import Session, select

from database.engine import ENGINE
from database.models import Run as RunDB
from database.models import Span as SpanDB
from database.models import User as UserDB


class UserRepository:
    @staticmethod
    def _dom_to_db(user: UserDom) -> UserDB:
        return UserDB(
            id=UUID(user.id),
            email=user.email,
            password=user.password,
            meta_data=user.meta_data,
        )

    @staticmethod
    def _db_to_dom(user_db: UserDB) -> UserDom:
        return UserDom(
            id=str(user_db.id),
            email=user_db.email,
            password=user_db.password,
            meta_data=user_db.meta_data,
        )

    @staticmethod
    def create(user: UserDom) -> UserDom:
        with Session(ENGINE) as session:
            session.add(UserRepository._dom_to_db(user))
            session.commit()
            return user

    @staticmethod
    def get(user_id: UUID_t) -> UserDom:
        with Session(ENGINE) as session:
            user_db = session.get(UserDB, user_id)
            return UserRepository._db_to_dom(user_db)

    @staticmethod
    def get_or_none(user_id: UUID_t) -> UserDom | None:
        with Session(ENGINE) as session:
            user_db = session.get(UserDB, user_id)
            return UserRepository._db_to_dom(user_db) if user_db else None

    @staticmethod
    def list() -> list[UserDom]:
        with Session(ENGINE) as session:
            rows = session.exec(select(UserDB).order_by(UserDB.created_at.desc())).all()
            return [UserRepository._db_to_dom(r) for r in rows]

    @staticmethod
    def update(user: UserDom) -> UserDom:
        with Session(ENGINE) as session:
            session.merge(UserRepository._dom_to_db(user))
            session.commit()
            return user

    @staticmethod
    def delete(user_id: UUID_t) -> None:
        with Session(ENGINE) as session:
            session.delete(UserDB(id=user_id))
            session.commit()


class RunRepository:
    @staticmethod
    def _dom_to_db(run: RunDom) -> RunDB:
        return RunDB(
            id=UUID(run.id),
            thread_id=run.thread_id,
            status=run.status,
            graph_signature=run.graph_signature,
            policy=run.policy,
            meta_data=run.meta_data,
        )

    @staticmethod
    def _db_to_dom(run_db: RunDB) -> RunDom:
        return RunDom(
            id=str(run_db.id),
            thread_id=run_db.thread_id,
            status=run_db.status,
            graph_signature=run_db.graph_signature,
            policy=run_db.policy,
            meta_data=run_db.meta_data,
        )

    @staticmethod
    def create(run: RunDom) -> RunDom:
        with Session(ENGINE) as session:
            session.add(RunRepository._dom_to_db(run))
            session.commit()
            return run

    @staticmethod
    def get(run_id: UUID_t) -> RunDom:
        with Session(ENGINE) as session:
            row = session.get(RunDB, run_id)
            return RunRepository._db_to_dom(row)

    @staticmethod
    def get_or_none(run_id: UUID_t) -> RunDom | None:
        with Session(ENGINE) as session:
            row = session.get(RunDB, run_id)
            return RunRepository._db_to_dom(row) if row else None

    @staticmethod
    def list() -> list[RunDom]:
        with Session(ENGINE) as session:
            rows = session.exec(select(RunDB).order_by(RunDB.created_at.desc())).all()
            return [RunRepository._db_to_dom(r) for r in rows]

    @staticmethod
    def update(run: RunDom) -> RunDom:
        with Session(ENGINE) as session:
            session.merge(RunRepository._dom_to_db(run))
            session.commit()
            return run

    @staticmethod
    def delete(run_id: UUID_t) -> None:
        with Session(ENGINE) as session:
            session.delete(RunDB(id=run_id))
            session.commit()


class SpanRepository:
    @staticmethod
    def _dom_to_db(span: SpanDom) -> SpanDB:
        return SpanDB(
            id=UUID(span.id),
            run_id=UUID(span.run_id),
            node_id=span.node_id,
            checkpoint_id=span.checkpoint_id,
            kind=span.kind,
            name=span.name,
            start_ts=span.start_ts,
            end_ts=span.end_ts,
            fingerprint=span.fingerprint,
            attrs=span.attrs,
        )

    @staticmethod
    def _db_to_dom(span_db: SpanDB) -> SpanDom:
        return SpanDom(
            id=str(span_db.id),
            run_id=str(span_db.run_id),
            node_id=span_db.node_id,
            checkpoint_id=span_db.checkpoint_id,
            kind=span_db.kind,
            name=span_db.name,
            start_ts=span_db.start_ts,
            end_ts=span_db.end_ts,
            fingerprint=span_db.fingerprint,
            attrs=span_db.attrs,
        )

    @staticmethod
    def create(span: SpanDom) -> SpanDom:
        with Session(ENGINE) as session:
            session.add(SpanRepository._dom_to_db(span))
            session.commit()
            return span

    @staticmethod
    def list_for_run(run_id: UUID_t) -> list[SpanDom]:
        with Session(ENGINE) as session:
            rows = session.exec(
                select(SpanDB)
                .where(SpanDB.run_id == run_id)
                .order_by(SpanDB.created_at)
            ).all()
            return [SpanRepository._db_to_dom(r) for r in rows]
