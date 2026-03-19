# IPAM CSV 导入单元测试
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.base import Base
from database.ipam_models import IpamAggregate, IpamPrefix
from services.ipam_csv_import import (
    AGGREGATE_CSV_HEADERS,
    PREFIX_CSV_HEADERS,
    aggregate_template_csv,
    prefix_template_csv,
    import_aggregates_csv,
    import_prefixes_csv,
)


def _db():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine, tables=[IpamAggregate.__table__, IpamPrefix.__table__])
    return sessionmaker(bind=engine, future=True)()


class AggregateCsvImportTests(unittest.TestCase):
    def test_wrong_header_raises(self):
        db = _db()
        bad = "\ufeff网段,错误列\n10.0.0.0/8,,,\n"
        with self.assertRaises(ValueError):
            import_aggregates_csv(db, bad)
        db.close()

    def test_import_new_aggregate(self):
        db = _db()
        header = "\ufeff" + ",".join(AGGREGATE_CSV_HEADERS) + "\n"
        csv_text = header + "10.0.0.0/8,RFC1918,2020-01-01,测试\n"
        imp, upd, fail, errs = import_aggregates_csv(db, csv_text)
        self.assertEqual((imp, upd, fail), (1, 0, 0))
        self.assertEqual(errs, [])
        row = db.query(IpamAggregate).filter(IpamAggregate.prefix == "10.0.0.0/8").first()
        self.assertIsNotNone(row)
        self.assertEqual(row.rir, "RFC1918")
        db.close()

    def test_duplicate_in_file(self):
        db = _db()
        header = "\ufeff" + ",".join(AGGREGATE_CSV_HEADERS) + "\n"
        csv_text = header + "10.0.0.0/8,,,\n10.0.0.0/8,,,\n"
        imp, upd, fail, errs = import_aggregates_csv(db, csv_text)
        self.assertEqual(imp, 1)
        self.assertEqual(fail, 1)
        self.assertTrue(any("重复" in e for e in errs))
        db.close()

    def test_template_matches_headers(self):
        t = aggregate_template_csv().lstrip("\ufeff").strip()
        self.assertEqual(t, ",".join(AGGREGATE_CSV_HEADERS))


class PrefixCsvImportTests(unittest.TestCase):
    def test_prefix_with_aggregate_cidr(self):
        db = _db()
        db.add(IpamAggregate(prefix="10.0.0.0/8", rir=None, date_added=None, description=None))
        db.commit()
        header = "\ufeff" + ",".join(PREFIX_CSV_HEADERS) + "\n"
        csv_text = header + "10.1.0.0/16,active,,否,否,,,10.0.0.0/8,\n"
        imp, upd, fail, errs = import_prefixes_csv(db, csv_text)
        self.assertEqual((imp, upd, fail), (1, 0, 0))
        self.assertEqual(errs, [])
        p = db.query(IpamPrefix).filter(IpamPrefix.prefix == "10.1.0.0/16").first()
        self.assertIsNotNone(p)
        self.assertIsNotNone(p.aggregate_id)
        db.close()

    def test_prefix_template_matches_headers(self):
        t = prefix_template_csv().lstrip("\ufeff").strip()
        self.assertEqual(t, ",".join(PREFIX_CSV_HEADERS))


if __name__ == "__main__":
    unittest.main()
