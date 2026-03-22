"""Tests for xml/write_xml_to_file.py and xml/xml_to_string.py."""

import xml.etree.ElementTree as et

from pacs008.xml.write_xml_to_file import indent_xml, write_xml_to_file
from pacs008.xml.xml_to_string import xml_to_string


class TestIndentXml:
    def test_indent_leaf_element(self):
        elem = et.Element("root")
        indent_xml(elem)
        # Leaf element at level 0 should not get tail
        assert elem.tail is None or elem.tail == ""

    def test_indent_with_children(self):
        root = et.Element("root")
        child1 = et.SubElement(root, "child1")
        child1.text = "value1"
        child2 = et.SubElement(root, "child2")
        child2.text = "value2"
        indent_xml(root)
        assert root.text is not None
        assert "\n" in root.text

    def test_indent_preserves_existing_text(self):
        root = et.Element("root")
        child = et.SubElement(root, "child")
        child.text = "keep this"
        indent_xml(root)
        assert child.text == "keep this"

    def test_indent_nested(self):
        root = et.Element("root")
        parent = et.SubElement(root, "parent")
        child = et.SubElement(parent, "child")
        child.text = "deep"
        indent_xml(root)
        # Check indentation levels
        assert "  " in parent.text

    def test_indent_multiple_levels(self):
        root = et.Element("a")
        b = et.SubElement(root, "b")
        c = et.SubElement(b, "c")
        d = et.SubElement(c, "d")
        d.text = "leaf"
        indent_xml(root, level=0)
        # d is at level 3, its tail should be "\n" + "  " * 3 (leaf at level 3)
        # But after parent processes children, d.tail = "\n" + "  " * 2 (to align with parent's closing tag)
        assert "\n" in d.tail

    def test_indent_empty_children(self):
        root = et.Element("root")
        et.SubElement(root, "empty1")
        et.SubElement(root, "empty2")
        indent_xml(root)
        # Empty children at level 1 should get tails


class TestWriteXmlToFile:
    def test_write_simple(self, tmp_path):
        root = et.Element("Document")
        child = et.SubElement(root, "Header")
        child.text = "test"
        out = tmp_path / "output.xml"
        write_xml_to_file(str(out), root)
        content = out.read_text(encoding="utf-8")
        assert "<?xml" in content
        assert "<Document>" in content
        assert "<Header>test</Header>" in content

    def test_write_preserves_structure(self, tmp_path):
        root = et.Element("root")
        parent = et.SubElement(root, "parent")
        et.SubElement(parent, "child1").text = "a"
        et.SubElement(parent, "child2").text = "b"
        out = tmp_path / "tree.xml"
        write_xml_to_file(str(out), root)
        content = out.read_text(encoding="utf-8")
        assert "<child1>a</child1>" in content
        assert "<child2>b</child2>" in content

    def test_write_with_attributes(self, tmp_path):
        root = et.Element("root")
        child = et.SubElement(root, "amount", Ccy="EUR")
        child.text = "100.00"
        out = tmp_path / "attr.xml"
        write_xml_to_file(str(out), root)
        content = out.read_text(encoding="utf-8")
        assert 'Ccy="EUR"' in content
        assert "100.00" in content


class TestXmlToString:
    def test_basic_conversion(self):
        root = et.Element("Document")
        child = et.SubElement(root, "Body")
        child.text = "content"
        result = xml_to_string(root)
        assert result.startswith("<?xml")
        assert "<Document>" in result
        assert "<Body>content</Body>" in result
        assert result.endswith("\n")

    def test_without_declaration(self):
        root = et.Element("root")
        result = xml_to_string(root, include_declaration=False)
        assert not result.startswith("<?xml")
        assert "<root" in result

    def test_with_declaration_already_present(self):
        # When element already has declaration-like content
        root = et.Element("root")
        result = xml_to_string(root, include_declaration=True)
        assert result.count("<?xml") == 1

    def test_trailing_newline(self):
        root = et.Element("root")
        result = xml_to_string(root)
        assert result.endswith("\n")

    def test_complex_tree(self):
        root = et.Element("Document")
        grp = et.SubElement(root, "GrpHdr")
        et.SubElement(grp, "MsgId").text = "MSG001"
        et.SubElement(grp, "NbOfTxs").text = "1"
        result = xml_to_string(root)
        assert "<MsgId>MSG001</MsgId>" in result
        assert "<NbOfTxs>1</NbOfTxs>" in result
