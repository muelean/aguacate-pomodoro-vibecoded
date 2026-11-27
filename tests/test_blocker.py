"""Tests del bloqueo con un archivo hosts FALSO en una carpeta temporal."""
import os
import tempfile
import unittest

from aguacate.blocker import (
    END, START, HostsCorrupt, HostsFile, add_block, clean_domains, has_block, strip_block,
)

ORIGINAL = (
    "# Copyright (c) 1993-2009 Microsoft Corp.\r\n"
    "#\r\n"
    "# localhost name resolution is handled within DNS itself.\r\n"
    "#\t127.0.0.1       localhost\r\n"
    "192.168.1.50 nas.local\r\n"
)
DOMAINS = ["youtube.com", "www.youtube.com", "chess.com"]


class TextTest(unittest.TestCase):
    def test_roundtrip_is_exact(self):
        blocked = add_block(ORIGINAL, DOMAINS, "\r\n")
        self.assertTrue(has_block(blocked))
        self.assertIn("127.0.0.1 youtube.com\r\n", blocked)
        self.assertIn("::1 chess.com\r\n", blocked)
        self.assertEqual(strip_block(blocked, "\r\n"), ORIGINAL)

    def test_no_trailing_newline(self):
        orig = "127.0.0.1 a.local"
        blocked = add_block(orig, DOMAINS, "\n")
        self.assertTrue(blocked.startswith("127.0.0.1 a.local\n"))
        self.assertEqual(strip_block(blocked, "\n"), orig + "\n")

    def test_add_twice_keeps_one_block(self):
        once = add_block(ORIGINAL, DOMAINS, "\r\n")
        twice = add_block(once, DOMAINS, "\r\n")
        self.assertEqual(once, twice)
        self.assertEqual(twice.count(START), 1)

    def test_corrupt_markers(self):
        for bad in (ORIGINAL + START + "\r\n",
                    ORIGINAL + END + "\r\n" + START + "\r\n",
                    ORIGINAL + START + "\r\n" + END + "\r\n" + START + "\r\n" + END + "\r\n"):
            with self.assertRaises(HostsCorrupt):
                has_block(bad)

    def test_clean_domains_rejects_garbage(self):
        self.assertEqual(
            clean_domains(["YouTube.com", "youtube.com", " chess.com. ", "evil.com\n1.2.3.4 bank.com",
                           "no espacios.com", "", "localhost", "colonist.io"]),
            ["youtube.com", "chess.com", "colonist.io"],
        )


class FileTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "hosts")
        self.backup = os.path.join(self.dir, "Aguacate", "hosts.backup")
        with open(self.path, "wb") as f:
            f.write(ORIGINAL.encode("utf-8"))
        self.flushes = 0

        def flush():
            self.flushes += 1

        self.h = HostsFile(self.path, self.backup, flush=flush)

    def read(self, p=None):
        with open(p or self.path, "rb") as f:
            return f.read()

    def test_block_unblock_restores_bytes(self):
        self.h.block(DOMAINS)
        self.assertTrue(self.h.is_blocked())
        self.assertIn(b"127.0.0.1 youtube.com\r\n", self.read())
        self.assertTrue(self.h.unblock())
        self.assertEqual(self.read(), ORIGINAL.encode("utf-8"))
        self.assertFalse(self.h.unblock())         # ya estaba limpio
        self.assertEqual(self.flushes, 2)

    def test_backup_only_once(self):
        self.h.block(DOMAINS)
        self.assertEqual(self.read(self.backup), ORIGINAL.encode("utf-8"))
        self.h.unblock()
        with open(self.path, "ab") as f:
            f.write(b"10.0.0.1 otro.local\r\n")
        self.h.block(DOMAINS)
        self.assertEqual(self.read(self.backup), ORIGINAL.encode("utf-8"))

    def test_recovery_after_crash(self):
        """Simula un cierre brusco: el bloque se queda; un nuevo HostsFile lo limpia."""
        self.h.block(DOMAINS)
        nuevo = HostsFile(self.path, self.backup, flush=lambda: None)
        self.assertTrue(nuevo.is_blocked())
        self.assertTrue(nuevo.unblock())
        self.assertEqual(self.read(), ORIGINAL.encode("utf-8"))

    def test_corrupt_file_is_not_touched(self):
        bad = (ORIGINAL + START + "\r\n127.0.0.1 youtube.com\r\n").encode()
        with open(self.path, "wb") as f:
            f.write(bad)
        with self.assertRaises(HostsCorrupt):
            self.h.block(DOMAINS)
        with self.assertRaises(HostsCorrupt):
            self.h.unblock()
        self.assertEqual(self.read(), bad)
        self.assertFalse(os.path.exists(self.backup))

    def test_bom_and_cp1252_preserved(self):
        for raw in (b"\xef\xbb\xbf127.0.0.1 a.local\r\n", "# caf\xe9\r\n".encode("cp1252")):
            with open(self.path, "wb") as f:
                f.write(raw)
            self.h.block(DOMAINS)
            self.h.unblock()
            self.assertEqual(self.read(), raw)

    def test_no_temp_file_left(self):
        self.h.block(DOMAINS)
        self.h.unblock()
        self.assertEqual(sorted(os.listdir(self.dir)), ["Aguacate", "hosts"])


if __name__ == "__main__":
    unittest.main()
