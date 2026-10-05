# Generic storage tools for the LLM agent, parameterized by mission.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.base import BaseTool


def _serialize(value):
    import datetime
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    return value


class SaveItemsTool(BaseTool):
    name = "save_items"
    description = "Save discovered items to the mission database with dedup. Args: {'items': [...], 'job_id': 'id'}"

    def __init__(self, mission):
        self.mission = mission

    def execute(self, items, job_id=None):
        session = self.mission.get_session()
        try:
            result = self.mission.save_new_items(session, items, job_id or "agent")
            session.commit()
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            session.close()


class QueryItemsTool(BaseTool):
    name = "query_items"
    description = "Query the mission database. Args: {'limit': 10, 'search': 'term'}"

    def __init__(self, mission):
        self.mission = mission

    def execute(self, limit=10, search=None):
        from sqlalchemy import or_
        session = self.mission.get_session()
        try:
            model = self.mission.model
            q = session.query(model)
            if search:
                conds = [
                    getattr(model, f).contains(search)
                    for f in self.mission.searchable_fields
                    if hasattr(model, f)
                ]
                if conds:
                    q = q.filter(or_(*conds))
            rows = q.order_by(model.id.desc()).limit(limit).all()
            cols = list(model.__table__.columns)
            items = [
                {c.name: _serialize(getattr(r, c.name)) for c in cols}
                for r in rows
            ]
            return {"success": True, "data": {"count": len(items), "items": items}}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            session.close()
