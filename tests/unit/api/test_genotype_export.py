"""Unit tests for Genotype export methods (HapMap, VCF, Numeric, Plink)."""

from unittest.mock import patch, MagicMock
from uuid import uuid4
from gemini.api.genotype import Genotype

MODULE = "gemini.api.genotype"


def _make_record(variant_name, chromosome, position, population_name, call_value, alleles="T/C"):
    mock = MagicMock()
    mock.variant_name = variant_name
    mock.chromosome = chromosome
    mock.position = position
    mock.population_name = population_name
    mock.call_value = call_value
    mock.alleles = alleles
    return mock


def _sample_records():
    """Create a small set of test records: 2 variants x 2 samples."""
    return [
        _make_record("1_100", 1, 10.0, "SampleA", "TT", "T/C"),
        _make_record("1_100", 1, 10.0, "SampleB", "CC", "T/C"),
        _make_record("2_200", 2, 20.0, "SampleA", "AA", "A/G"),
        _make_record("2_200", 2, 20.0, "SampleB", "GG", "A/G"),
    ]


class TestExportHapMap:
    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_hapmap_structure(self, m):
        m.filter_records.return_value = _sample_records()
        g = Genotype(genotype_name="test", id=uuid4())
        output = g.export(format="hapmap")

        lines = output.strip().split("\n")
        assert len(lines) == 3  # header + 2 variants

        # Check header
        header = lines[0].split("\t")
        assert header[0] == "rs#"
        assert header[1] == "alleles"
        assert header[2] == "chrom"
        assert header[3] == "pos"
        assert "SampleA" in header
        assert "SampleB" in header

        # Check first data row
        row1 = lines[1].split("\t")
        assert row1[0] == "1_100"
        assert row1[2] == "1"  # chromosome

    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_hapmap_homozygous_encoding(self, m):
        m.filter_records.return_value = _sample_records()
        g = Genotype(genotype_name="test", id=uuid4())
        output = g.export(format="hapmap")

        lines = output.strip().split("\n")
        row1 = lines[1].split("\t")
        # For "TT" homozygous, should encode as single letter "T"
        sample_a_idx = lines[0].split("\t").index("SampleA")
        assert row1[sample_a_idx] == "T"


class TestExportVCF:
    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_vcf_structure(self, m):
        m.filter_records.return_value = _sample_records()
        g = Genotype(genotype_name="test", id=uuid4())
        output = g.export(format="vcf")

        lines = output.strip().split("\n")
        # Should have ##fileformat, ##source, #CHROM header, and 2 data lines
        assert lines[0].startswith("##fileformat=VCF")
        assert lines[1].startswith("##source=")
        assert lines[2].startswith("#CHROM")

        header = lines[2].split("\t")
        assert header[0] == "#CHROM"
        assert header[3] == "REF"
        assert header[4] == "ALT"
        assert header[8] == "FORMAT"

    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_vcf_genotype_encoding(self, m):
        m.filter_records.return_value = _sample_records()
        g = Genotype(genotype_name="test", id=uuid4())
        output = g.export(format="vcf")

        lines = output.strip().split("\n")
        header = lines[2].split("\t")
        data = lines[3].split("\t")

        # First variant: alleles T/C, SampleA=TT (ref/ref = 0/0), SampleB=CC (alt/alt = 1/1)
        sample_a_idx = header.index("SampleA")
        sample_b_idx = header.index("SampleB")
        assert data[sample_a_idx] == "0/0"
        assert data[sample_b_idx] == "1/1"


class TestExportNumeric:
    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_numeric_012_structure(self, m):
        m.filter_records.return_value = _sample_records()
        g = Genotype(genotype_name="test", id=uuid4())
        output = g.export(format="numeric", coding="012")

        lines = output.strip().split("\n")
        assert len(lines) == 3  # header + 2 samples

        header = lines[0].split("\t")
        assert header[0] == "taxa"
        assert "1_100" in header
        assert "2_200" in header

    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_numeric_012_values(self, m):
        m.filter_records.return_value = _sample_records()
        g = Genotype(genotype_name="test", id=uuid4())
        output = g.export(format="numeric", coding="012")

        lines = output.strip().split("\n")
        header = lines[0].split("\t")

        # Find SampleA row
        for line in lines[1:]:
            parts = line.split("\t")
            if parts[0] == "SampleA":
                v1_idx = header.index("1_100")
                # SampleA has TT for T/C variant -> 0 alt alleles = 0
                assert parts[v1_idx] == "0"
                v2_idx = header.index("2_200")
                # SampleA has AA for A/G variant -> 0 alt alleles = 0
                assert parts[v2_idx] == "0"

    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_numeric_negative101(self, m):
        m.filter_records.return_value = _sample_records()
        g = Genotype(genotype_name="test", id=uuid4())
        output = g.export(format="numeric", coding="-101")

        lines = output.strip().split("\n")
        header = lines[0].split("\t")

        for line in lines[1:]:
            parts = line.split("\t")
            if parts[0] == "SampleB":
                v1_idx = header.index("1_100")
                # SampleB has CC for T/C variant -> 2 alt alleles, -101 coding: 2-1=1
                assert parts[v1_idx] == "1"


class TestExportPlink:
    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_plink_structure(self, m):
        m.filter_records.return_value = _sample_records()
        g = Genotype(genotype_name="test", id=uuid4())
        output = g.export(format="plink")

        assert "# PED" in output
        assert "# MAP" in output

    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_plink_ped_format(self, m):
        m.filter_records.return_value = _sample_records()
        g = Genotype(genotype_name="test", id=uuid4())
        output = g.export(format="plink")

        ped_section = output.split("# MAP")[0].replace("# PED\n", "")
        ped_lines = [l for l in ped_section.strip().split("\n") if l]
        assert len(ped_lines) == 2  # 2 samples

        parts = ped_lines[0].split("\t")
        # First 6 columns: FID, IID, paternal, maternal, sex, phenotype
        assert parts[2] == "0"  # paternal
        assert parts[3] == "0"  # maternal
        # Then 2 allele columns per variant (2 variants = 4 allele columns)
        assert len(parts) == 6 + 4


class TestExportEmpty:
    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_empty_records(self, m):
        m.filter_records.return_value = []
        g = Genotype(genotype_name="test", id=uuid4())
        output = g.export(format="hapmap")
        assert output == ""


class TestExportInvalidFormat:
    @patch(f"{MODULE}.GenotypeRecordModel")
    def test_invalid_format(self, m):
        m.filter_records.return_value = _sample_records()
        g = Genotype(genotype_name="test", id=uuid4())
        try:
            g.export(format="invalid")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
