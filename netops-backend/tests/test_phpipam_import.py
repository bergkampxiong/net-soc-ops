# phpIPAM 导入：解析与写入逻辑单元测试
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.base import Base
from database.ipam_models import IpamAggregate, IpamPrefix
from services.phpipam_import import apply_phpipam_subnets_to_db, fetch_phpipam_subnets


def _memory_db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        engine,
        tables=[IpamAggregate.__table__, IpamPrefix.__table__],
    )
    Session = sessionmaker(bind=engine, future=True)
    return Session()


class PhpipamImportDbTests(unittest.TestCase):
    """folder -> Aggregate，叶子 -> Prefix，并关联 aggregate_id"""

    def test_folder_and_leaf_aggregate_link(self):
        db = _memory_db_session()
        raw = [
            {"subnet": "10.0.0.0", "mask": 8, "isFolder": "1", "description": "根"},
            {"subnet": "10.10.0.0", "mask": 16, "isFolder": "0", "description": "子网"},
        ]
        ac, au, pc, pu = apply_phpipam_subnets_to_db(db, raw)
        self.assertEqual((ac, au, pc, pu), (1, 0, 1, 0))
        pref = db.query(IpamPrefix).filter(IpamPrefix.prefix == "10.10.0.0/16").first()
        self.assertIsNotNone(pref)
        self.assertIsNotNone(pref.aggregate_id)
        agg = db.query(IpamAggregate).filter(IpamAggregate.id == pref.aggregate_id).first()
        self.assertEqual(agg.prefix, "10.0.0.0/8")
        db.close()

    def test_invalid_cidr_skipped(self):
        db = _memory_db_session()
        raw = [
            {"subnet": "999.0.0.0", "mask": 24, "isFolder": "0"},
        ]
        ac, au, pc, pu = apply_phpipam_subnets_to_db(db, raw)
        self.assertEqual((ac, au, pc, pu), (0, 0, 0, 0))
        db.close()

    def test_update_existing_prefix(self):
        db = _memory_db_session()
        db.add(IpamAggregate(prefix="10.0.0.0/8", rir=None, date_added=None, description=None))
        db.add(IpamPrefix(prefix="10.1.0.0/24", status="active", description="old", is_pool=False, mark_utilized=False))
        db.commit()
        raw = [
            {"subnet": "10.1.0.0", "mask": 24, "isFolder": "0", "description": "新描述"},
        ]
        ac, au, pc, pu = apply_phpipam_subnets_to_db(db, raw)
        self.assertEqual(pu, 1)
        self.assertEqual(pc, 0)
        pref = db.query(IpamPrefix).filter(IpamPrefix.prefix == "10.1.0.0/24").first()
        self.assertEqual(pref.description, "新描述")
        db.close()


class PhpipamFetchTests(unittest.TestCase):
    @patch("services.phpipam_import.requests.get")
    def test_fetch_parses_list_data(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "code": 200,
            "success": True,
            "data": [{"subnet": "192.168.0.0", "mask": 24, "isFolder": 0}],
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        rows = fetch_phpipam_subnets("https://ipam.test/api/app1", "secret-token")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["subnet"], "192.168.0.0")

    @patch("services.phpipam_import.requests.get")
    def test_fetch_single_object_data(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "code": 200,
            "data": {"subnet": "10.0.0.0", "mask": 8, "isFolder": 1},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        rows = fetch_phpipam_subnets("https://ipam.test/api/app1", "t")
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
