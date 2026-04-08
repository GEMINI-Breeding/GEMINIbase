"""
Genomic test fixture data extracted from real cowpea MAGIC population dataset.

Source: tpj13827-sup-0004-datas1.xlsx (Huynh et al., The Plant Journal)
Species: Vigna unguiculata (cowpea)
Population: 8-parent MAGIC (Multi-parent Advanced Generation Inter-Cross)

Contains a representative subset: 50 SNP variants (5 per chromosome, chr 1-10),
10 samples (8 founders + 2 MAGIC lines), 500 genotype calls, and flowering
time phenotype data.
"""


FIXTURE_VARIANTS = [
    {
        "variant_name": "2_24641",
        "chromosome": 1,
        "position": 0.0,
        "alleles": "T/C",
        "design_sequence": "AGACGAGTAGCTTTGGTCGAAGGTTGATTCAAGTCGCCGAAGCTCATAATTGAGTCGACT[T/C]GACTCAAACTAAATATCGAGACGACTCGCCTGAGCTGAAGATCGATATGAGTCGATTTAT",
    },
    {
        "variant_name": "2_30714",
        "chromosome": 1,
        "position": 11.20083074,
        "alleles": "C/A",
        "design_sequence": "TATGTTGTCAGAAATCATCATTAGAACGATTCCTAAGATAGTTATTACAAAAGTGTAACA[C/A]TCTAATCATACATGCCAGTTTGTGATATTTGACACTGTAAGTGCAAATATTGTTTATTCA",
    },
    {
        "variant_name": "2_22731",
        "chromosome": 1,
        "position": 21.67472687,
        "alleles": "C/T",
        "design_sequence": "TGACAGTCAGTACAATTGCTTATCACCAATTTAGATGGAMATAAAGTTCTACTTTTTCTT[C/T]GAGGAATTCATTTCTCCTTGTTTGAATCATGTGTAGTTTAGGCTGCAACTTTTGTAAAAY",
    },
    {
        "variant_name": "2_46692",
        "chromosome": 1,
        "position": 53.96717989,
        "alleles": "A/G",
        "design_sequence": "GCGAGGAACAGCAGCATGTACCTTTTAAGAAAATCATTGACATAAAATGAGCTTGCTGAA[A/G]TATTAAGAGAAGCTAATACATGACGATSACCAGTTCAGTTGGTCTACTATGCAATAAAAA",
    },
    {
        "variant_name": "2_48745",
        "chromosome": 1,
        "position": 86.3425679,
        "alleles": "C/T",
        "design_sequence": "TTTTGTATGGTCATGATCACATCTATGTTGACAATTGTGAAGGTTTGAATGTTCTTGCAT[C/T]TGCTCGACTTCTTTGTCATCCTACCCACTTATCTTTTACTTTCAATCTTCATTATTTACT",
    },
    {
        "variant_name": "2_54033",
        "chromosome": 2,
        "position": 0.0,
        "alleles": "G/A",
        "design_sequence": "AATAGTCAATTTATACACAATGGCAAGCAATACCCGCAACATTCTATAGTATCTACAAGT[G/A]CCTATAAGYATACCTAT-TTTTTTTCTATACMTTCCCACAYAATKAACAATTTCATGTTT",
    },
    {
        "variant_name": "2_51927",
        "chromosome": 2,
        "position": 7.119897288,
        "alleles": "G/A",
        "design_sequence": "CAATCTTGTGTTTCACAAAAGGAGAAGTTGTTGTCCAAGGAACTATGTACTGGATTTTAT[G/A]TAATAATTTGTAATTTGCATTTCATATATTGTTCCTAGCCTGTTTTAGTCCAAACCACTG",
    },
    {
        "variant_name": "2_05109",
        "chromosome": 2,
        "position": 26.20558251,
        "alleles": "C/A",
        "design_sequence": "AACTCAATTAGTTGAGGCAGCAAAGACATTTGAGGYTCTAGAGATCTAAAACCTGATCTA[C/A]CCATCTATCACCAGGGTAGGAAACGTAGCAAATATAAGAAGAAATCTCATTACCTCCGCT",
    },
    {
        "variant_name": "2_11944",
        "chromosome": 2,
        "position": 41.28785849,
        "alleles": "T/C",
        "design_sequence": "ATGGATCAATGACCTACCTAAATTCACCCGTAGAATCTTAAGTAACAACCTACCATTTAT[T/C]AAATTAACGTTTAATAAAACCTTGTTAAAAATATAGCATGTCCCAGGTGTTCATTAATCC",
    },
    {
        "variant_name": "2_01828",
        "chromosome": 2,
        "position": 72.56537023,
        "alleles": "T/C",
        "design_sequence": "GAAATAGCCCTAAACTGAAATACAACATTCTTGCCTGAAAATTTTGTGCAGCAAGAGGGT[T/C]ATTTGGATTTTTATCTGGATGCACCTGCCTTGCCTGCACATCAAGTATTGAAGAGAAGGT",
    },
    {
        "variant_name": "2_04899",
        "chromosome": 3,
        "position": 0.0,
        "alleles": "C/T",
        "design_sequence": "AATGATCATGCCCATTCATGTAAAAATCAATATTATTTGCCTGAAATTTGAAATTAAAAT[C/T]AGCCCAGTTGGTTAGAGAACAAGGATCATGTTCAGTTCTTAGCTTTTAGTTACCTGAAGG",
    },
    {
        "variant_name": "2_21454",
        "chromosome": 3,
        "position": 30.95852953,
        "alleles": "G/A",
        "design_sequence": "TTCAGTGAATCACTCAGTCCCTTTGGAATGGAAGAAGAAGAAGYTCCGATTCTGCGACTG[G/A]AAATTCTGCAAGGCCCTGGCGAAGGCAAAACCCTAGACTTCAAACCCGGATCCGCCGTCC",
    },
    {
        "variant_name": "2_30955",
        "chromosome": 3,
        "position": 52.05370604,
        "alleles": "A/G",
        "design_sequence": "-TTTTACTCACTATAAGATTCAAACTGTATAAATGCAAACAAGGATATTTAGTAGCAAAG[A/G]TTAAGTGCTAAAAAATGAACATTATCTTACCGTTTTGTCTTAGGTAACAGTCTTGTCTCC",
    },
    {
        "variant_name": "2_00657",
        "chromosome": 3,
        "position": 93.22654837,
        "alleles": "A/G",
        "design_sequence": "TCGGACCAGTCGCGAAGCTTCTTGAGCGCCCTCAGGCCACGCGACCACCATCGGTCACCG[A/G]AGGAAGGMGAATTGGAGTGGGACCAGGAGGTGGAGCGGACGCGCTCCCACCACGAGGAAC",
    },
    {
        "variant_name": "2_21403",
        "chromosome": 3,
        "position": 132.6856107,
        "alleles": "C/T",
        "design_sequence": "CTGAGATCATAATTATTTATAAACTTTAAAGTACTGCATTTGATTGACATAACTAAAGCA[C/T]CAGGTTCTTATCAAATAATTAAGTAGTTAGCGAAATTGATACAAACCTTATTACCAATTG",
    },
    {
        "variant_name": "2_45166",
        "chromosome": 4,
        "position": 0.0,
        "alleles": "A/G",
        "design_sequence": "CCTTCTTCTCTCTCCCTCCCCTCTCTCCATGTATATGTATATATACGAAAAAGGAGAATG[A/G]TTTTTTSACTACTGAATTTTGACAACTTTTTCTCATAATCTTACATGTTATTTTTTAAGT",
    },
    {
        "variant_name": "2_18175",
        "chromosome": 4,
        "position": 27.50359604,
        "alleles": "A/G",
        "design_sequence": "ACCAACTGGTAGGAGCTTTGGAACACAAGATAATGTACTAGGTTCAAGTTCATATGTGGT[A/G]TTGCAAATGCACCACTTAGCAAGATTYGAATTCTGCATACAGTGCACCAGATASTTGAAT",
    },
    {
        "variant_name": "2_39529",
        "chromosome": 4,
        "position": 31.02545911,
        "alleles": "A/G",
        "design_sequence": "CAAGGTCATTTAGAACCRGAGGACAYGTGACTCTACATGAGAGCTAGAGGAAGATATGAG[A/G]AAGTCATATTTGCATCTGCTTTTTGGTAAGTCTTAATTTTCGAGGTCTAAAATTTTTGTT",
    },
    {
        "variant_name": "2_51744",
        "chromosome": 4,
        "position": 40.49601636,
        "alleles": "T/C",
        "design_sequence": "GTTGCCTTTATTTGTTAAGGTGGGTTGGCATTGCAACTGATCACGAAATCTTGTCCAATC[T/C]TATAATTGGATGTCCTGGAATTAAAGAATTTCCATATCTATGGTTTTAACAGTTAAGTTT",
    },
    {
        "variant_name": "2_26383",
        "chromosome": 4,
        "position": 78.70162576,
        "alleles": "G/A",
        "design_sequence": "ATAATAGSGGTTAAAAAAGAATCTAGTACCTAAAGAATGTCATTCATTATACCCTACTAT[G/A]ATTTTACTTGACAAATAYAGAAGGATGAAGTACTAGGAAAGGGATGAAAAGTGCAAGACA",
    },
    {
        "variant_name": "2_15811",
        "chromosome": 5,
        "position": 0.0,
        "alleles": "C/T",
        "design_sequence": "CTTTAGGATTTCTTCCATTTCTCTTTAGAAGGTTTGAACAGGGAAATGTGGAAGAAAAGT[C/T]ACAAGTGGTGTCACTCTTGCTAAATTGTATTCAAGTAGACTCTGGTTGCATATATAAGAT",
    },
    {
        "variant_name": "2_22101",
        "chromosome": 5,
        "position": 18.24101023,
        "alleles": "C/A",
        "design_sequence": "AAGCCAACACATTCTTCAGTATATATAATACTCAGAGTAGACCACAAGGATGAACCATAG[C/A]CAATTGTCAACTCCTCTGTATCAGCTTGATCTTTAACTAAAAGTTCAAAATATGCCAGTT",
    },
    {
        "variant_name": "2_44345",
        "chromosome": 5,
        "position": 45.90389456,
        "alleles": "T/C",
        "design_sequence": "AAACACGCATCCATAGAGTCCTTCTTCCTCTCGATTTTGTTGAAGGAGCAAAGAAGCTAG[T/C]CATTGCTCCATCAAACTATTCAATTTTCACCTTTTCTTCATTCACAACAACCATTGCTCC",
    },
    {
        "variant_name": "2_43785",
        "chromosome": 5,
        "position": 56.41845307,
        "alleles": "T/C",
        "design_sequence": "ATCAATCTATGCTCGATGAATTCCAAAAATTCATTGCTTCCCAATCGCAAGCCAACATAG[T/C]CTTGCAATCTTAAGGTACATAATCACCAAATATATCTCTTGACAAATGAATCACTAATTT",
    },
    {
        "variant_name": "2_32577",
        "chromosome": 5,
        "position": 106.9259993,
        "alleles": "T/A",
        "design_sequence": "GAGCACKTGTATCTTCTTGTAACTTATATCTAACAGTGGCAGAATTCAATACCATTTGAT[T/A]GGAACACTTCAGATTTGAATATTTGCACTGTATACTTGATAATATCTTTTATATGACTAG",
    },
    {
        "variant_name": "2_37985",
        "chromosome": 6,
        "position": 0.0,
        "alleles": "G/A",
        "design_sequence": "TTAGTTGTCAAAGAAGCTTTATCAAAACGTGATGGTGAGTGTGACAAAAGAAAGAGAAAA[G/A]ACGATGTCTCTGGTGGAACCCAAAAAAGGAGCAGCTTATGGGTGTAATTGAACAATAATA",
    },
    {
        "variant_name": "2_31421",
        "chromosome": 6,
        "position": 2.797262507,
        "alleles": "C/T",
        "design_sequence": "TGAATCAAATTACAGTTAGTTGTGCTTGAATTACCATGTTGTAAAGATGTCTTACAATTT[C/T]ATAATCTTCCTCTACTTGTGTATGTCACCACTATAGTGCACACTGTTATGTCATGGATTG",
    },
    {
        "variant_name": "2_15875",
        "chromosome": 6,
        "position": 32.28509449,
        "alleles": "T/G",
        "design_sequence": "TGTTGTAAAACCATGACCCACACTCAGTCTTATTGGTTGGGAACTGTATATGKACAGAAT[T/G]ACTACCCAAATTCTTAAAACCAATCGACATTTTGGCTTGAAGCTTTGGGTTTCCTCTGTG",
    },
    {
        "variant_name": "2_21361",
        "chromosome": 6,
        "position": 49.98734185,
        "alleles": "G/A",
        "design_sequence": "TCAAATGAGGCTCTACAATAATTGAGCCATAAATCAAAAGATCTGTCTCCAAAATCAAAA[G/A]AATCTAGTCATTGAGGAAGAACAGGAGGAGCTATTGCACGAGTATTGTATGAGTTGCAGT",
    },
    {
        "variant_name": "2_08495",
        "chromosome": 6,
        "position": 80.60530411,
        "alleles": "T/C",
        "design_sequence": "TTACAAAGCTTTGGCAAACTAAAATCATTCAGGTTAGGAACTACTCCTTCTACCCTATAA[T/C]AATTGCACTTTCAAGTTTCTTCATACGAACAATAATAAATATTTGAGAATTAAGTTGAGC",
    },
    {
        "variant_name": "1_1364",
        "chromosome": 7,
        "position": 0.0,
        "alleles": "G/A",
        "design_sequence": "CATGTAAATATTTTAGGAAACAGGAATTCGGTCGTATACAACCATCAAATTCAGAGGACG[G/A]AGTAAGTTCTCCTCAAGTCTACGTACAGGTTACTCCTGCCACTATGAAAAATGACAAAAA",
    },
    {
        "variant_name": "2_03358",
        "chromosome": 7,
        "position": 37.0464522,
        "alleles": "G/A",
        "design_sequence": "GTTTTCAAAAGCTAAAAGGCTTACGTAATTAATTTTTCAGCATCAAATTTCATAGCTCTA[G/A]CAGCATTTACTGATATAAGTTGGTGATATTGGATTTCCTATTCAAAGGCAAGCTGAATTC",
    },
    {
        "variant_name": "2_17932",
        "chromosome": 7,
        "position": 57.24056118,
        "alleles": "A/G",
        "design_sequence": "GAATAS-GATCAGATCAYTAAAAAAATGCTTGTGTGATGATATCCATTTTTTGTGGCTTC[A/G]GCATAAAAAAATACTAGTTTAGTCACCAAATTTGAACAGGGTGCCCTGCTTTGATTCTGA",
    },
    {
        "variant_name": "2_08738",
        "chromosome": 7,
        "position": 86.91757606,
        "alleles": "C/A",
        "design_sequence": "TTGCATGTCCACAATTAACGTACTAAAGCACTACAAACTATGATGAAAATGTTGGGACTT[C/A]AAATAAAGAATAACCAGTTAACCAGGAGCATGTCCTGTTTTTTTTGGGCCGCCAGTGGCA",
    },
    {
        "variant_name": "2_10600",
        "chromosome": 7,
        "position": 104.9474657,
        "alleles": "C/A",
        "design_sequence": "AACAGATTGCATAAGAGACTTTCAATAATATCTATATCTATACATTACAAATAGGACACA[C/A]TTTCGAAAGAAAAGTTTTAGAGAGATTAAGAGGGATTGATATAGAGTTCTCCACAAGAAA",
    },
    {
        "variant_name": "2_20179",
        "chromosome": 8,
        "position": 0.0,
        "alleles": "G/A",
        "design_sequence": "AAATTTTATGAAAACTGTTAAGGGATTTCTACATTAACATCCTATACATCACAAAGTTAA[G/A]CGACCAGCTTCCTTTTGGCACCTTGATTCTAGTARTCTCACTGTTATTAATTAATAGACA",
    },
    {
        "variant_name": "2_15967",
        "chromosome": 8,
        "position": 25.35359262,
        "alleles": "G/A",
        "design_sequence": "GCCCAGGAAGAACATCTCTGCAACTGTTCTACTAGAAATAAAGGGAGGATGTAAGTTGTT[G/A]AGTCAATTTTAGAGTAGGTTCACCCACTATTACTCTAAATCTTTGCTTGTCTCTACTCTC",
    },
    {
        "variant_name": "2_50531",
        "chromosome": 8,
        "position": 36.64739787,
        "alleles": "A/G",
        "design_sequence": "ATAAATTCATATGATAAATACAAAATATTTTGCTATAAAATACCATTTCTTGCAACACAA[A/G]TTATAAATATGCTATACAACAAAAATGTTATTTAAAATATTCATCCCTTATACTAATATG",
    },
    {
        "variant_name": "2_15282",
        "chromosome": 8,
        "position": 55.1575382,
        "alleles": "C/A",
        "design_sequence": "CACTACTTTATCAGAGCTGAGAAAAGATGCACACACTTCTGTTTACACCATACGCCAAGG[C/A]AAAATGCTAACTCCGGAACAGCAAGCTGATCCTACTAATTATGCAGATTGCATCCATTGG",
    },
    {
        "variant_name": "2_48268",
        "chromosome": 8,
        "position": 78.11356115,
        "alleles": "A/G",
        "design_sequence": "ATTTTACTACCATCAGCTCCAGCTTCATTATCCGACTTGTCGGTACCTGTTTCATCCGCT[A/G]CTTTGGGCAACGGTATTTGGACTTTCTGCACCTCCACATGAAGTGATATTGAAGATGGTT",
    },
    {
        "variant_name": "2_46176",
        "chromosome": 9,
        "position": 0.0,
        "alleles": "A/G",
        "design_sequence": "AACCTCGTGCTAGCCCCGTAGAATCCCAAAAGCCAAAAAGTGAATCCAGAAGCTCCGAAT[A/G]AGACTCT-GTGGTAATTTTTTTGGTATGGYGTGTGAATCTTTTTTTATTTTTCTGTGTGA",
    },
    {
        "variant_name": "2_04550",
        "chromosome": 9,
        "position": 30.73456094,
        "alleles": "G/A",
        "design_sequence": "GCAAAGTATTCTGGTGGCAGGCACACAATGTGCATAACATAACCTGTCTAAATATTTACT[G/A]AAGGAAATGATACCTCAAAGTTGAACCCTGCACTTGCAGTCTTGTTTTCACAACATCCAA",
    },
    {
        "variant_name": "2_12293",
        "chromosome": 9,
        "position": 45.70421179,
        "alleles": "T/C",
        "design_sequence": "ATGARGCTAAATCCTAATAAGAACCTCTGCAAATATGACAGTGTAATTTCTTTTAACGCA[T/C]TCTTCATTATTGATTGAAAATTAGTGAAAAACASAGAATTGTGCTGGTCTTACTTCTTAC",
    },
    {
        "variant_name": "2_15253",
        "chromosome": 9,
        "position": 58.5178538,
        "alleles": "A/G",
        "design_sequence": "ATTCAAAACTTTACTCACTCCACTATTCCAAACCTTGCTGGGGTAAGGTAAGAAAAATTG[A/G]TGAATAAAAGGTTAGGACATGCTGAATTTGATTAATTAAAACAGAAAACAAAGTAGTCAT",
    },
    {
        "variant_name": "2_30204",
        "chromosome": 9,
        "position": 97.14235451,
        "alleles": "C/T",
        "design_sequence": "GGAGAAATTTACCTATGTGAGTTTCAGTGACATTCGCAAGGTAGCTATCTAGTTGCTAGA[C/T]GAGTGGGATTGTAGGCATCACCCGTTGAGCGAATGGATGATTTCGTTGAGTGAATGCATT",
    },
    {
        "variant_name": "2_29305",
        "chromosome": 10,
        "position": 0.0,
        "alleles": "G/A",
        "design_sequence": "AATAATACTTAAGAGTCTAGGTTGAGCAAACAGAACAAAGCTCAATTGATCCATAATCAA[G/A]CAACTCTTGAATCATCTGCTCTATGTGATCATCTTCAAGAACGGGTTGAAATTGCTGATG",
    },
    {
        "variant_name": "2_33791",
        "chromosome": 10,
        "position": 9.88613132,
        "alleles": "A/T",
        "design_sequence": "GAACAAAGCAATGGATATGGAACACCTGTACTCTGTTGTCTGTGCAGATAAATCGATGAA[A/T]GATGACCCTTTTGCTTCTCACGTTCTTCGTATTTCGTTCCAAGAATCTTGGATTTCTTAA",
    },
    {
        "variant_name": "2_46304",
        "chromosome": 10,
        "position": 13.45498434,
        "alleles": "G/A",
        "design_sequence": "CTACGTGTTATATRTATGAGGATSATATCTCATCAAAATAAATACGTTTTCTGAGTTAAT[G/A]TAAGTGTTCATAAATATTGGAGAGAAATTTACTATAGGAACTTGTATTAGTGAAGTCATA",
    },
    {
        "variant_name": "2_55108",
        "chromosome": 10,
        "position": 34.0221336,
        "alleles": "T/C",
        "design_sequence": "TAGTTCCCCCAGTTACGTAAGCGTGGCTGAAGTGATCCAAGAAATGGAACACTGCAAACG[T/C]GAACTAGTTCATGTCATTTATAGTTTRTCCAAAGACATGGGGTTCCCWGGTTTCAGAGTT",
    },
    {
        "variant_name": "2_32654",
        "chromosome": 10,
        "position": 70.83729212,
        "alleles": "A/T",
        "design_sequence": "TTGATTTCTAATTGATGGTTTCATCATTGTCAGAAATTGAGGATCGTCAGTGGTTGAGAC[A/T]ATGGGTAAAGAGAAAGTCTCACAAACCCCAAGAAGAATGACAAGGTCTTCGGCTTCATCT",
    },
]


FIXTURE_POPULATIONS = [
    {
        "population_name": "IT89KD-288",
        "population_accession": "IT89KD-288",
    },
    {
        "population_name": "IT84S-2049",
        "population_accession": "IT84S-2049",
    },
    {
        "population_name": "CB27",
        "population_accession": "CB27",
    },
    {
        "population_name": "IT82E-18",
        "population_accession": "IT82E-18",
    },
    {
        "population_name": "Suvita 2",
        "population_accession": "Suvita 2",
    },
    {
        "population_name": "IT00K-1263",
        "population_accession": "IT00K-1263",
    },
    {
        "population_name": "IT84S-2246",
        "population_accession": "IT84S-2246",
    },
    {
        "population_name": "IT93K-503-1",
        "population_accession": "IT93K-503-1",
    },
    {
        "population_name": "MAGIC001",
        "population_accession": "MAGIC001",
    },
    {
        "population_name": "MAGIC002",
        "population_accession": "MAGIC002",
    },
]


FIXTURE_GENOTYPE_CALLS = [
    {
        "variant_name": "2_24641",
        "population_name": "IT89KD-288",
        "call_value": "TT",
    },
    {
        "variant_name": "2_24641",
        "population_name": "IT84S-2049",
        "call_value": "CC",
    },
    {
        "variant_name": "2_24641",
        "population_name": "CB27",
        "call_value": "CC",
    },
    {
        "variant_name": "2_24641",
        "population_name": "IT82E-18",
        "call_value": "TT",
    },
    {
        "variant_name": "2_24641",
        "population_name": "Suvita 2",
        "call_value": "CC",
    },
    {
        "variant_name": "2_24641",
        "population_name": "IT00K-1263",
        "call_value": "TT",
    },
    {
        "variant_name": "2_24641",
        "population_name": "IT84S-2246",
        "call_value": "TT",
    },
    {
        "variant_name": "2_24641",
        "population_name": "IT93K-503-1",
        "call_value": "TT",
    },
    {
        "variant_name": "2_24641",
        "population_name": "MAGIC001",
        "call_value": "TT",
    },
    {
        "variant_name": "2_24641",
        "population_name": "MAGIC002",
        "call_value": "TT",
    },
    {
        "variant_name": "2_30714",
        "population_name": "IT89KD-288",
        "call_value": "AA",
    },
    {
        "variant_name": "2_30714",
        "population_name": "IT84S-2049",
        "call_value": "CC",
    },
    {
        "variant_name": "2_30714",
        "population_name": "CB27",
        "call_value": "CC",
    },
    {
        "variant_name": "2_30714",
        "population_name": "IT82E-18",
        "call_value": "CC",
    },
    {
        "variant_name": "2_30714",
        "population_name": "Suvita 2",
        "call_value": "AA",
    },
    {
        "variant_name": "2_30714",
        "population_name": "IT00K-1263",
        "call_value": "CC",
    },
    {
        "variant_name": "2_30714",
        "population_name": "IT84S-2246",
        "call_value": "CC",
    },
    {
        "variant_name": "2_30714",
        "population_name": "IT93K-503-1",
        "call_value": "AA",
    },
    {
        "variant_name": "2_30714",
        "population_name": "MAGIC001",
        "call_value": "AA",
    },
    {
        "variant_name": "2_30714",
        "population_name": "MAGIC002",
        "call_value": "CC",
    },
    {
        "variant_name": "2_22731",
        "population_name": "IT89KD-288",
        "call_value": "TT",
    },
    {
        "variant_name": "2_22731",
        "population_name": "IT84S-2049",
        "call_value": "TT",
    },
    {
        "variant_name": "2_22731",
        "population_name": "CB27",
        "call_value": "TT",
    },
    {
        "variant_name": "2_22731",
        "population_name": "IT82E-18",
        "call_value": "TT",
    },
    {
        "variant_name": "2_22731",
        "population_name": "Suvita 2",
        "call_value": "TT",
    },
    {
        "variant_name": "2_22731",
        "population_name": "IT00K-1263",
        "call_value": "CC",
    },
    {
        "variant_name": "2_22731",
        "population_name": "IT84S-2246",
        "call_value": "TT",
    },
    {
        "variant_name": "2_22731",
        "population_name": "IT93K-503-1",
        "call_value": "CC",
    },
    {
        "variant_name": "2_22731",
        "population_name": "MAGIC001",
        "call_value": "CC",
    },
    {
        "variant_name": "2_22731",
        "population_name": "MAGIC002",
        "call_value": "TT",
    },
    {
        "variant_name": "2_46692",
        "population_name": "IT89KD-288",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46692",
        "population_name": "IT84S-2049",
        "call_value": "AA",
    },
    {
        "variant_name": "2_46692",
        "population_name": "CB27",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46692",
        "population_name": "IT82E-18",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46692",
        "population_name": "Suvita 2",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46692",
        "population_name": "IT00K-1263",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46692",
        "population_name": "IT84S-2246",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46692",
        "population_name": "IT93K-503-1",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46692",
        "population_name": "MAGIC001",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46692",
        "population_name": "MAGIC002",
        "call_value": "GG",
    },
    {
        "variant_name": "2_48745",
        "population_name": "IT89KD-288",
        "call_value": "CC",
    },
    {
        "variant_name": "2_48745",
        "population_name": "IT84S-2049",
        "call_value": "TT",
    },
    {
        "variant_name": "2_48745",
        "population_name": "CB27",
        "call_value": "TT",
    },
    {
        "variant_name": "2_48745",
        "population_name": "IT82E-18",
        "call_value": "CC",
    },
    {
        "variant_name": "2_48745",
        "population_name": "Suvita 2",
        "call_value": "CC",
    },
    {
        "variant_name": "2_48745",
        "population_name": "IT00K-1263",
        "call_value": "CC",
    },
    {
        "variant_name": "2_48745",
        "population_name": "IT84S-2246",
        "call_value": "CC",
    },
    {
        "variant_name": "2_48745",
        "population_name": "IT93K-503-1",
        "call_value": "TT",
    },
    {
        "variant_name": "2_48745",
        "population_name": "MAGIC001",
        "call_value": "CC",
    },
    {
        "variant_name": "2_48745",
        "population_name": "MAGIC002",
        "call_value": "CC",
    },
    {
        "variant_name": "2_54033",
        "population_name": "IT89KD-288",
        "call_value": "AA",
    },
    {
        "variant_name": "2_54033",
        "population_name": "IT84S-2049",
        "call_value": "GG",
    },
    {
        "variant_name": "2_54033",
        "population_name": "CB27",
        "call_value": "GG",
    },
    {
        "variant_name": "2_54033",
        "population_name": "IT82E-18",
        "call_value": "AA",
    },
    {
        "variant_name": "2_54033",
        "population_name": "Suvita 2",
        "call_value": "GG",
    },
    {
        "variant_name": "2_54033",
        "population_name": "IT00K-1263",
        "call_value": "AA",
    },
    {
        "variant_name": "2_54033",
        "population_name": "IT84S-2246",
        "call_value": "AA",
    },
    {
        "variant_name": "2_54033",
        "population_name": "IT93K-503-1",
        "call_value": "AA",
    },
    {
        "variant_name": "2_54033",
        "population_name": "MAGIC001",
        "call_value": "GG",
    },
    {
        "variant_name": "2_54033",
        "population_name": "MAGIC002",
        "call_value": "GG",
    },
    {
        "variant_name": "2_51927",
        "population_name": "IT89KD-288",
        "call_value": "GG",
    },
    {
        "variant_name": "2_51927",
        "population_name": "IT84S-2049",
        "call_value": "AA",
    },
    {
        "variant_name": "2_51927",
        "population_name": "CB27",
        "call_value": "AA",
    },
    {
        "variant_name": "2_51927",
        "population_name": "IT82E-18",
        "call_value": "AA",
    },
    {
        "variant_name": "2_51927",
        "population_name": "Suvita 2",
        "call_value": "AA",
    },
    {
        "variant_name": "2_51927",
        "population_name": "IT00K-1263",
        "call_value": "AA",
    },
    {
        "variant_name": "2_51927",
        "population_name": "IT84S-2246",
        "call_value": "GG",
    },
    {
        "variant_name": "2_51927",
        "population_name": "IT93K-503-1",
        "call_value": "GG",
    },
    {
        "variant_name": "2_51927",
        "population_name": "MAGIC001",
        "call_value": "GG",
    },
    {
        "variant_name": "2_51927",
        "population_name": "MAGIC002",
        "call_value": "AA",
    },
    {
        "variant_name": "2_05109",
        "population_name": "IT89KD-288",
        "call_value": "AA",
    },
    {
        "variant_name": "2_05109",
        "population_name": "IT84S-2049",
        "call_value": "AA",
    },
    {
        "variant_name": "2_05109",
        "population_name": "CB27",
        "call_value": "CC",
    },
    {
        "variant_name": "2_05109",
        "population_name": "IT82E-18",
        "call_value": "CC",
    },
    {
        "variant_name": "2_05109",
        "population_name": "Suvita 2",
        "call_value": "CC",
    },
    {
        "variant_name": "2_05109",
        "population_name": "IT00K-1263",
        "call_value": "CC",
    },
    {
        "variant_name": "2_05109",
        "population_name": "IT84S-2246",
        "call_value": "AA",
    },
    {
        "variant_name": "2_05109",
        "population_name": "IT93K-503-1",
        "call_value": "AA",
    },
    {
        "variant_name": "2_05109",
        "population_name": "MAGIC001",
        "call_value": "CC",
    },
    {
        "variant_name": "2_05109",
        "population_name": "MAGIC002",
        "call_value": "CC",
    },
    {
        "variant_name": "2_11944",
        "population_name": "IT89KD-288",
        "call_value": "TT",
    },
    {
        "variant_name": "2_11944",
        "population_name": "IT84S-2049",
        "call_value": "TT",
    },
    {
        "variant_name": "2_11944",
        "population_name": "CB27",
        "call_value": "CC",
    },
    {
        "variant_name": "2_11944",
        "population_name": "IT82E-18",
        "call_value": "TT",
    },
    {
        "variant_name": "2_11944",
        "population_name": "Suvita 2",
        "call_value": "CC",
    },
    {
        "variant_name": "2_11944",
        "population_name": "IT00K-1263",
        "call_value": "TT",
    },
    {
        "variant_name": "2_11944",
        "population_name": "IT84S-2246",
        "call_value": "TT",
    },
    {
        "variant_name": "2_11944",
        "population_name": "IT93K-503-1",
        "call_value": "TT",
    },
    {
        "variant_name": "2_11944",
        "population_name": "MAGIC001",
        "call_value": "CC",
    },
    {
        "variant_name": "2_11944",
        "population_name": "MAGIC002",
        "call_value": "CC",
    },
    {
        "variant_name": "2_01828",
        "population_name": "IT89KD-288",
        "call_value": "TT",
    },
    {
        "variant_name": "2_01828",
        "population_name": "IT84S-2049",
        "call_value": "TT",
    },
    {
        "variant_name": "2_01828",
        "population_name": "CB27",
        "call_value": "TT",
    },
    {
        "variant_name": "2_01828",
        "population_name": "IT82E-18",
        "call_value": "CC",
    },
    {
        "variant_name": "2_01828",
        "population_name": "Suvita 2",
        "call_value": "CC",
    },
    {
        "variant_name": "2_01828",
        "population_name": "IT00K-1263",
        "call_value": "TT",
    },
    {
        "variant_name": "2_01828",
        "population_name": "IT84S-2246",
        "call_value": "TT",
    },
    {
        "variant_name": "2_01828",
        "population_name": "IT93K-503-1",
        "call_value": "TT",
    },
    {
        "variant_name": "2_01828",
        "population_name": "MAGIC001",
        "call_value": "CC",
    },
    {
        "variant_name": "2_01828",
        "population_name": "MAGIC002",
        "call_value": "TT",
    },
    {
        "variant_name": "2_04899",
        "population_name": "IT89KD-288",
        "call_value": "CC",
    },
    {
        "variant_name": "2_04899",
        "population_name": "IT84S-2049",
        "call_value": "CC",
    },
    {
        "variant_name": "2_04899",
        "population_name": "CB27",
        "call_value": "CC",
    },
    {
        "variant_name": "2_04899",
        "population_name": "IT82E-18",
        "call_value": "TT",
    },
    {
        "variant_name": "2_04899",
        "population_name": "Suvita 2",
        "call_value": "CC",
    },
    {
        "variant_name": "2_04899",
        "population_name": "IT00K-1263",
        "call_value": "CC",
    },
    {
        "variant_name": "2_04899",
        "population_name": "IT84S-2246",
        "call_value": "CC",
    },
    {
        "variant_name": "2_04899",
        "population_name": "IT93K-503-1",
        "call_value": "CC",
    },
    {
        "variant_name": "2_04899",
        "population_name": "MAGIC001",
        "call_value": "CC",
    },
    {
        "variant_name": "2_04899",
        "population_name": "MAGIC002",
        "call_value": "CC",
    },
    {
        "variant_name": "2_21454",
        "population_name": "IT89KD-288",
        "call_value": "GG",
    },
    {
        "variant_name": "2_21454",
        "population_name": "IT84S-2049",
        "call_value": "GG",
    },
    {
        "variant_name": "2_21454",
        "population_name": "CB27",
        "call_value": "GG",
    },
    {
        "variant_name": "2_21454",
        "population_name": "IT82E-18",
        "call_value": "AA",
    },
    {
        "variant_name": "2_21454",
        "population_name": "Suvita 2",
        "call_value": "GG",
    },
    {
        "variant_name": "2_21454",
        "population_name": "IT00K-1263",
        "call_value": "AA",
    },
    {
        "variant_name": "2_21454",
        "population_name": "IT84S-2246",
        "call_value": "GG",
    },
    {
        "variant_name": "2_21454",
        "population_name": "IT93K-503-1",
        "call_value": "GG",
    },
    {
        "variant_name": "2_21454",
        "population_name": "MAGIC001",
        "call_value": "GG",
    },
    {
        "variant_name": "2_21454",
        "population_name": "MAGIC002",
        "call_value": "GG",
    },
    {
        "variant_name": "2_30955",
        "population_name": "IT89KD-288",
        "call_value": "GG",
    },
    {
        "variant_name": "2_30955",
        "population_name": "IT84S-2049",
        "call_value": "GG",
    },
    {
        "variant_name": "2_30955",
        "population_name": "CB27",
        "call_value": "GG",
    },
    {
        "variant_name": "2_30955",
        "population_name": "IT82E-18",
        "call_value": "GG",
    },
    {
        "variant_name": "2_30955",
        "population_name": "Suvita 2",
        "call_value": "GG",
    },
    {
        "variant_name": "2_30955",
        "population_name": "IT00K-1263",
        "call_value": "AA",
    },
    {
        "variant_name": "2_30955",
        "population_name": "IT84S-2246",
        "call_value": "GG",
    },
    {
        "variant_name": "2_30955",
        "population_name": "IT93K-503-1",
        "call_value": "GG",
    },
    {
        "variant_name": "2_30955",
        "population_name": "MAGIC001",
        "call_value": "GG",
    },
    {
        "variant_name": "2_30955",
        "population_name": "MAGIC002",
        "call_value": "GG",
    },
    {
        "variant_name": "2_00657",
        "population_name": "IT89KD-288",
        "call_value": "AA",
    },
    {
        "variant_name": "2_00657",
        "population_name": "IT84S-2049",
        "call_value": "AA",
    },
    {
        "variant_name": "2_00657",
        "population_name": "CB27",
        "call_value": "AA",
    },
    {
        "variant_name": "2_00657",
        "population_name": "IT82E-18",
        "call_value": "GG",
    },
    {
        "variant_name": "2_00657",
        "population_name": "Suvita 2",
        "call_value": "AA",
    },
    {
        "variant_name": "2_00657",
        "population_name": "IT00K-1263",
        "call_value": "AA",
    },
    {
        "variant_name": "2_00657",
        "population_name": "IT84S-2246",
        "call_value": "AA",
    },
    {
        "variant_name": "2_00657",
        "population_name": "IT93K-503-1",
        "call_value": "AA",
    },
    {
        "variant_name": "2_00657",
        "population_name": "MAGIC001",
        "call_value": "AA",
    },
    {
        "variant_name": "2_00657",
        "population_name": "MAGIC002",
        "call_value": "AA",
    },
    {
        "variant_name": "2_21403",
        "population_name": "IT89KD-288",
        "call_value": "CC",
    },
    {
        "variant_name": "2_21403",
        "population_name": "IT84S-2049",
        "call_value": "CC",
    },
    {
        "variant_name": "2_21403",
        "population_name": "CB27",
        "call_value": "TT",
    },
    {
        "variant_name": "2_21403",
        "population_name": "IT82E-18",
        "call_value": "CC",
    },
    {
        "variant_name": "2_21403",
        "population_name": "Suvita 2",
        "call_value": "CC",
    },
    {
        "variant_name": "2_21403",
        "population_name": "IT00K-1263",
        "call_value": "CC",
    },
    {
        "variant_name": "2_21403",
        "population_name": "IT84S-2246",
        "call_value": "CC",
    },
    {
        "variant_name": "2_21403",
        "population_name": "IT93K-503-1",
        "call_value": "CC",
    },
    {
        "variant_name": "2_21403",
        "population_name": "MAGIC001",
        "call_value": "CC",
    },
    {
        "variant_name": "2_21403",
        "population_name": "MAGIC002",
        "call_value": "CC",
    },
    {
        "variant_name": "2_45166",
        "population_name": "IT89KD-288",
        "call_value": "AA",
    },
    {
        "variant_name": "2_45166",
        "population_name": "IT84S-2049",
        "call_value": "AA",
    },
    {
        "variant_name": "2_45166",
        "population_name": "CB27",
        "call_value": "GG",
    },
    {
        "variant_name": "2_45166",
        "population_name": "IT82E-18",
        "call_value": "AA",
    },
    {
        "variant_name": "2_45166",
        "population_name": "Suvita 2",
        "call_value": "AA",
    },
    {
        "variant_name": "2_45166",
        "population_name": "IT00K-1263",
        "call_value": "AA",
    },
    {
        "variant_name": "2_45166",
        "population_name": "IT84S-2246",
        "call_value": "GG",
    },
    {
        "variant_name": "2_45166",
        "population_name": "IT93K-503-1",
        "call_value": "AA",
    },
    {
        "variant_name": "2_45166",
        "population_name": "MAGIC001",
        "call_value": "AA",
    },
    {
        "variant_name": "2_45166",
        "population_name": "MAGIC002",
        "call_value": "AA",
    },
    {
        "variant_name": "2_18175",
        "population_name": "IT89KD-288",
        "call_value": "AA",
    },
    {
        "variant_name": "2_18175",
        "population_name": "IT84S-2049",
        "call_value": "AA",
    },
    {
        "variant_name": "2_18175",
        "population_name": "CB27",
        "call_value": "AA",
    },
    {
        "variant_name": "2_18175",
        "population_name": "IT82E-18",
        "call_value": "GG",
    },
    {
        "variant_name": "2_18175",
        "population_name": "Suvita 2",
        "call_value": "AA",
    },
    {
        "variant_name": "2_18175",
        "population_name": "IT00K-1263",
        "call_value": "GG",
    },
    {
        "variant_name": "2_18175",
        "population_name": "IT84S-2246",
        "call_value": "AA",
    },
    {
        "variant_name": "2_18175",
        "population_name": "IT93K-503-1",
        "call_value": "AA",
    },
    {
        "variant_name": "2_18175",
        "population_name": "MAGIC001",
        "call_value": "AA",
    },
    {
        "variant_name": "2_18175",
        "population_name": "MAGIC002",
        "call_value": "GG",
    },
    {
        "variant_name": "2_39529",
        "population_name": "IT89KD-288",
        "call_value": "AA",
    },
    {
        "variant_name": "2_39529",
        "population_name": "IT84S-2049",
        "call_value": "AA",
    },
    {
        "variant_name": "2_39529",
        "population_name": "CB27",
        "call_value": "AA",
    },
    {
        "variant_name": "2_39529",
        "population_name": "IT82E-18",
        "call_value": "GG",
    },
    {
        "variant_name": "2_39529",
        "population_name": "Suvita 2",
        "call_value": "AA",
    },
    {
        "variant_name": "2_39529",
        "population_name": "IT00K-1263",
        "call_value": "GG",
    },
    {
        "variant_name": "2_39529",
        "population_name": "IT84S-2246",
        "call_value": "AA",
    },
    {
        "variant_name": "2_39529",
        "population_name": "IT93K-503-1",
        "call_value": "AA",
    },
    {
        "variant_name": "2_39529",
        "population_name": "MAGIC001",
        "call_value": "AA",
    },
    {
        "variant_name": "2_39529",
        "population_name": "MAGIC002",
        "call_value": "AA",
    },
    {
        "variant_name": "2_51744",
        "population_name": "IT89KD-288",
        "call_value": "TT",
    },
    {
        "variant_name": "2_51744",
        "population_name": "IT84S-2049",
        "call_value": "CC",
    },
    {
        "variant_name": "2_51744",
        "population_name": "CB27",
        "call_value": "CC",
    },
    {
        "variant_name": "2_51744",
        "population_name": "IT82E-18",
        "call_value": "TT",
    },
    {
        "variant_name": "2_51744",
        "population_name": "Suvita 2",
        "call_value": "CC",
    },
    {
        "variant_name": "2_51744",
        "population_name": "IT00K-1263",
        "call_value": "CC",
    },
    {
        "variant_name": "2_51744",
        "population_name": "IT84S-2246",
        "call_value": "TT",
    },
    {
        "variant_name": "2_51744",
        "population_name": "IT93K-503-1",
        "call_value": "TT",
    },
    {
        "variant_name": "2_51744",
        "population_name": "MAGIC001",
        "call_value": "TT",
    },
    {
        "variant_name": "2_51744",
        "population_name": "MAGIC002",
        "call_value": "TT",
    },
    {
        "variant_name": "2_26383",
        "population_name": "IT89KD-288",
        "call_value": "GG",
    },
    {
        "variant_name": "2_26383",
        "population_name": "IT84S-2049",
        "call_value": "GG",
    },
    {
        "variant_name": "2_26383",
        "population_name": "CB27",
        "call_value": "GG",
    },
    {
        "variant_name": "2_26383",
        "population_name": "IT82E-18",
        "call_value": "GG",
    },
    {
        "variant_name": "2_26383",
        "population_name": "Suvita 2",
        "call_value": "GG",
    },
    {
        "variant_name": "2_26383",
        "population_name": "IT00K-1263",
        "call_value": "AA",
    },
    {
        "variant_name": "2_26383",
        "population_name": "IT84S-2246",
        "call_value": "GG",
    },
    {
        "variant_name": "2_26383",
        "population_name": "IT93K-503-1",
        "call_value": "GG",
    },
    {
        "variant_name": "2_26383",
        "population_name": "MAGIC001",
        "call_value": "GG",
    },
    {
        "variant_name": "2_26383",
        "population_name": "MAGIC002",
        "call_value": "GG",
    },
    {
        "variant_name": "2_15811",
        "population_name": "IT89KD-288",
        "call_value": "CC",
    },
    {
        "variant_name": "2_15811",
        "population_name": "IT84S-2049",
        "call_value": "CC",
    },
    {
        "variant_name": "2_15811",
        "population_name": "CB27",
        "call_value": "TT",
    },
    {
        "variant_name": "2_15811",
        "population_name": "IT82E-18",
        "call_value": "CC",
    },
    {
        "variant_name": "2_15811",
        "population_name": "Suvita 2",
        "call_value": "CC",
    },
    {
        "variant_name": "2_15811",
        "population_name": "IT00K-1263",
        "call_value": "TT",
    },
    {
        "variant_name": "2_15811",
        "population_name": "IT84S-2246",
        "call_value": "CC",
    },
    {
        "variant_name": "2_15811",
        "population_name": "IT93K-503-1",
        "call_value": "CC",
    },
    {
        "variant_name": "2_15811",
        "population_name": "MAGIC001",
        "call_value": "CC",
    },
    {
        "variant_name": "2_15811",
        "population_name": "MAGIC002",
        "call_value": "CC",
    },
    {
        "variant_name": "2_22101",
        "population_name": "IT89KD-288",
        "call_value": "CC",
    },
    {
        "variant_name": "2_22101",
        "population_name": "IT84S-2049",
        "call_value": "CC",
    },
    {
        "variant_name": "2_22101",
        "population_name": "CB27",
        "call_value": "CC",
    },
    {
        "variant_name": "2_22101",
        "population_name": "IT82E-18",
        "call_value": "CC",
    },
    {
        "variant_name": "2_22101",
        "population_name": "Suvita 2",
        "call_value": "CC",
    },
    {
        "variant_name": "2_22101",
        "population_name": "IT00K-1263",
        "call_value": "AA",
    },
    {
        "variant_name": "2_22101",
        "population_name": "IT84S-2246",
        "call_value": "CC",
    },
    {
        "variant_name": "2_22101",
        "population_name": "IT93K-503-1",
        "call_value": "CC",
    },
    {
        "variant_name": "2_22101",
        "population_name": "MAGIC001",
        "call_value": "CC",
    },
    {
        "variant_name": "2_22101",
        "population_name": "MAGIC002",
        "call_value": "CC",
    },
    {
        "variant_name": "2_44345",
        "population_name": "IT89KD-288",
        "call_value": "TT",
    },
    {
        "variant_name": "2_44345",
        "population_name": "IT84S-2049",
        "call_value": "CC",
    },
    {
        "variant_name": "2_44345",
        "population_name": "CB27",
        "call_value": "TT",
    },
    {
        "variant_name": "2_44345",
        "population_name": "IT82E-18",
        "call_value": "TT",
    },
    {
        "variant_name": "2_44345",
        "population_name": "Suvita 2",
        "call_value": "TT",
    },
    {
        "variant_name": "2_44345",
        "population_name": "IT00K-1263",
        "call_value": "TT",
    },
    {
        "variant_name": "2_44345",
        "population_name": "IT84S-2246",
        "call_value": "TT",
    },
    {
        "variant_name": "2_44345",
        "population_name": "IT93K-503-1",
        "call_value": "TT",
    },
    {
        "variant_name": "2_44345",
        "population_name": "MAGIC001",
        "call_value": "TT",
    },
    {
        "variant_name": "2_44345",
        "population_name": "MAGIC002",
        "call_value": "TT",
    },
    {
        "variant_name": "2_43785",
        "population_name": "IT89KD-288",
        "call_value": "CC",
    },
    {
        "variant_name": "2_43785",
        "population_name": "IT84S-2049",
        "call_value": "CC",
    },
    {
        "variant_name": "2_43785",
        "population_name": "CB27",
        "call_value": "CC",
    },
    {
        "variant_name": "2_43785",
        "population_name": "IT82E-18",
        "call_value": "TT",
    },
    {
        "variant_name": "2_43785",
        "population_name": "Suvita 2",
        "call_value": "CC",
    },
    {
        "variant_name": "2_43785",
        "population_name": "IT00K-1263",
        "call_value": "CC",
    },
    {
        "variant_name": "2_43785",
        "population_name": "IT84S-2246",
        "call_value": "CC",
    },
    {
        "variant_name": "2_43785",
        "population_name": "IT93K-503-1",
        "call_value": "CC",
    },
    {
        "variant_name": "2_43785",
        "population_name": "MAGIC001",
        "call_value": "TT",
    },
    {
        "variant_name": "2_43785",
        "population_name": "MAGIC002",
        "call_value": "CC",
    },
    {
        "variant_name": "2_32577",
        "population_name": "IT89KD-288",
        "call_value": "TT",
    },
    {
        "variant_name": "2_32577",
        "population_name": "IT84S-2049",
        "call_value": "AA",
    },
    {
        "variant_name": "2_32577",
        "population_name": "CB27",
        "call_value": "AA",
    },
    {
        "variant_name": "2_32577",
        "population_name": "IT82E-18",
        "call_value": "AA",
    },
    {
        "variant_name": "2_32577",
        "population_name": "Suvita 2",
        "call_value": "TT",
    },
    {
        "variant_name": "2_32577",
        "population_name": "IT00K-1263",
        "call_value": "AA",
    },
    {
        "variant_name": "2_32577",
        "population_name": "IT84S-2246",
        "call_value": "TT",
    },
    {
        "variant_name": "2_32577",
        "population_name": "IT93K-503-1",
        "call_value": "TT",
    },
    {
        "variant_name": "2_32577",
        "population_name": "MAGIC001",
        "call_value": "AA",
    },
    {
        "variant_name": "2_32577",
        "population_name": "MAGIC002",
        "call_value": "AA",
    },
    {
        "variant_name": "2_37985",
        "population_name": "IT89KD-288",
        "call_value": "GG",
    },
    {
        "variant_name": "2_37985",
        "population_name": "IT84S-2049",
        "call_value": "GG",
    },
    {
        "variant_name": "2_37985",
        "population_name": "CB27",
        "call_value": "GG",
    },
    {
        "variant_name": "2_37985",
        "population_name": "IT82E-18",
        "call_value": "GG",
    },
    {
        "variant_name": "2_37985",
        "population_name": "Suvita 2",
        "call_value": "AA",
    },
    {
        "variant_name": "2_37985",
        "population_name": "IT00K-1263",
        "call_value": "GG",
    },
    {
        "variant_name": "2_37985",
        "population_name": "IT84S-2246",
        "call_value": "GG",
    },
    {
        "variant_name": "2_37985",
        "population_name": "IT93K-503-1",
        "call_value": "GG",
    },
    {
        "variant_name": "2_37985",
        "population_name": "MAGIC001",
        "call_value": "GG",
    },
    {
        "variant_name": "2_37985",
        "population_name": "MAGIC002",
        "call_value": "GG",
    },
    {
        "variant_name": "2_31421",
        "population_name": "IT89KD-288",
        "call_value": "CC",
    },
    {
        "variant_name": "2_31421",
        "population_name": "IT84S-2049",
        "call_value": "TT",
    },
    {
        "variant_name": "2_31421",
        "population_name": "CB27",
        "call_value": "CC",
    },
    {
        "variant_name": "2_31421",
        "population_name": "IT82E-18",
        "call_value": "TT",
    },
    {
        "variant_name": "2_31421",
        "population_name": "Suvita 2",
        "call_value": "TT",
    },
    {
        "variant_name": "2_31421",
        "population_name": "IT00K-1263",
        "call_value": "TT",
    },
    {
        "variant_name": "2_31421",
        "population_name": "IT84S-2246",
        "call_value": "TT",
    },
    {
        "variant_name": "2_31421",
        "population_name": "IT93K-503-1",
        "call_value": "CC",
    },
    {
        "variant_name": "2_31421",
        "population_name": "MAGIC001",
        "call_value": "CC",
    },
    {
        "variant_name": "2_31421",
        "population_name": "MAGIC002",
        "call_value": "TT",
    },
    {
        "variant_name": "2_15875",
        "population_name": "IT89KD-288",
        "call_value": "TT",
    },
    {
        "variant_name": "2_15875",
        "population_name": "IT84S-2049",
        "call_value": "GG",
    },
    {
        "variant_name": "2_15875",
        "population_name": "CB27",
        "call_value": "TT",
    },
    {
        "variant_name": "2_15875",
        "population_name": "IT82E-18",
        "call_value": "TT",
    },
    {
        "variant_name": "2_15875",
        "population_name": "Suvita 2",
        "call_value": "TT",
    },
    {
        "variant_name": "2_15875",
        "population_name": "IT00K-1263",
        "call_value": "TT",
    },
    {
        "variant_name": "2_15875",
        "population_name": "IT84S-2246",
        "call_value": "TT",
    },
    {
        "variant_name": "2_15875",
        "population_name": "IT93K-503-1",
        "call_value": "TT",
    },
    {
        "variant_name": "2_15875",
        "population_name": "MAGIC001",
        "call_value": "TT",
    },
    {
        "variant_name": "2_15875",
        "population_name": "MAGIC002",
        "call_value": "TT",
    },
    {
        "variant_name": "2_21361",
        "population_name": "IT89KD-288",
        "call_value": "GG",
    },
    {
        "variant_name": "2_21361",
        "population_name": "IT84S-2049",
        "call_value": "GG",
    },
    {
        "variant_name": "2_21361",
        "population_name": "CB27",
        "call_value": "GG",
    },
    {
        "variant_name": "2_21361",
        "population_name": "IT82E-18",
        "call_value": "GG",
    },
    {
        "variant_name": "2_21361",
        "population_name": "Suvita 2",
        "call_value": "AA",
    },
    {
        "variant_name": "2_21361",
        "population_name": "IT00K-1263",
        "call_value": "GG",
    },
    {
        "variant_name": "2_21361",
        "population_name": "IT84S-2246",
        "call_value": "GG",
    },
    {
        "variant_name": "2_21361",
        "population_name": "IT93K-503-1",
        "call_value": "GG",
    },
    {
        "variant_name": "2_21361",
        "population_name": "MAGIC001",
        "call_value": "GG",
    },
    {
        "variant_name": "2_21361",
        "population_name": "MAGIC002",
        "call_value": "GG",
    },
    {
        "variant_name": "2_08495",
        "population_name": "IT89KD-288",
        "call_value": "CC",
    },
    {
        "variant_name": "2_08495",
        "population_name": "IT84S-2049",
        "call_value": "CC",
    },
    {
        "variant_name": "2_08495",
        "population_name": "CB27",
        "call_value": "TT",
    },
    {
        "variant_name": "2_08495",
        "population_name": "IT82E-18",
        "call_value": "CC",
    },
    {
        "variant_name": "2_08495",
        "population_name": "Suvita 2",
        "call_value": "TT",
    },
    {
        "variant_name": "2_08495",
        "population_name": "IT00K-1263",
        "call_value": "CC",
    },
    {
        "variant_name": "2_08495",
        "population_name": "IT84S-2246",
        "call_value": "CC",
    },
    {
        "variant_name": "2_08495",
        "population_name": "IT93K-503-1",
        "call_value": "CC",
    },
    {
        "variant_name": "2_08495",
        "population_name": "MAGIC001",
        "call_value": "TT",
    },
    {
        "variant_name": "2_08495",
        "population_name": "MAGIC002",
        "call_value": "CC",
    },
    {
        "variant_name": "1_1364",
        "population_name": "IT89KD-288",
        "call_value": "GG",
    },
    {
        "variant_name": "1_1364",
        "population_name": "IT84S-2049",
        "call_value": "AA",
    },
    {
        "variant_name": "1_1364",
        "population_name": "CB27",
        "call_value": "GG",
    },
    {
        "variant_name": "1_1364",
        "population_name": "IT82E-18",
        "call_value": "GG",
    },
    {
        "variant_name": "1_1364",
        "population_name": "Suvita 2",
        "call_value": "GG",
    },
    {
        "variant_name": "1_1364",
        "population_name": "IT00K-1263",
        "call_value": "GG",
    },
    {
        "variant_name": "1_1364",
        "population_name": "IT84S-2246",
        "call_value": "GG",
    },
    {
        "variant_name": "1_1364",
        "population_name": "IT93K-503-1",
        "call_value": "GG",
    },
    {
        "variant_name": "1_1364",
        "population_name": "MAGIC001",
        "call_value": "GG",
    },
    {
        "variant_name": "1_1364",
        "population_name": "MAGIC002",
        "call_value": "GG",
    },
    {
        "variant_name": "2_03358",
        "population_name": "IT89KD-288",
        "call_value": "GG",
    },
    {
        "variant_name": "2_03358",
        "population_name": "IT84S-2049",
        "call_value": "GG",
    },
    {
        "variant_name": "2_03358",
        "population_name": "CB27",
        "call_value": "GG",
    },
    {
        "variant_name": "2_03358",
        "population_name": "IT82E-18",
        "call_value": "AA",
    },
    {
        "variant_name": "2_03358",
        "population_name": "Suvita 2",
        "call_value": "GG",
    },
    {
        "variant_name": "2_03358",
        "population_name": "IT00K-1263",
        "call_value": "AA",
    },
    {
        "variant_name": "2_03358",
        "population_name": "IT84S-2246",
        "call_value": "GG",
    },
    {
        "variant_name": "2_03358",
        "population_name": "IT93K-503-1",
        "call_value": "GG",
    },
    {
        "variant_name": "2_03358",
        "population_name": "MAGIC001",
        "call_value": "GG",
    },
    {
        "variant_name": "2_03358",
        "population_name": "MAGIC002",
        "call_value": "AA",
    },
    {
        "variant_name": "2_17932",
        "population_name": "IT89KD-288",
        "call_value": "GG",
    },
    {
        "variant_name": "2_17932",
        "population_name": "IT84S-2049",
        "call_value": "GG",
    },
    {
        "variant_name": "2_17932",
        "population_name": "CB27",
        "call_value": "GG",
    },
    {
        "variant_name": "2_17932",
        "population_name": "IT82E-18",
        "call_value": "AA",
    },
    {
        "variant_name": "2_17932",
        "population_name": "Suvita 2",
        "call_value": "GG",
    },
    {
        "variant_name": "2_17932",
        "population_name": "IT00K-1263",
        "call_value": "GG",
    },
    {
        "variant_name": "2_17932",
        "population_name": "IT84S-2246",
        "call_value": "GG",
    },
    {
        "variant_name": "2_17932",
        "population_name": "IT93K-503-1",
        "call_value": "GG",
    },
    {
        "variant_name": "2_17932",
        "population_name": "MAGIC001",
        "call_value": "GG",
    },
    {
        "variant_name": "2_17932",
        "population_name": "MAGIC002",
        "call_value": "GG",
    },
    {
        "variant_name": "2_08738",
        "population_name": "IT89KD-288",
        "call_value": "CC",
    },
    {
        "variant_name": "2_08738",
        "population_name": "IT84S-2049",
        "call_value": "CC",
    },
    {
        "variant_name": "2_08738",
        "population_name": "CB27",
        "call_value": "CC",
    },
    {
        "variant_name": "2_08738",
        "population_name": "IT82E-18",
        "call_value": "AA",
    },
    {
        "variant_name": "2_08738",
        "population_name": "Suvita 2",
        "call_value": "CC",
    },
    {
        "variant_name": "2_08738",
        "population_name": "IT00K-1263",
        "call_value": "CC",
    },
    {
        "variant_name": "2_08738",
        "population_name": "IT84S-2246",
        "call_value": "CC",
    },
    {
        "variant_name": "2_08738",
        "population_name": "IT93K-503-1",
        "call_value": "CC",
    },
    {
        "variant_name": "2_08738",
        "population_name": "MAGIC001",
        "call_value": "CC",
    },
    {
        "variant_name": "2_08738",
        "population_name": "MAGIC002",
        "call_value": "CC",
    },
    {
        "variant_name": "2_10600",
        "population_name": "IT89KD-288",
        "call_value": "CC",
    },
    {
        "variant_name": "2_10600",
        "population_name": "IT84S-2049",
        "call_value": "CC",
    },
    {
        "variant_name": "2_10600",
        "population_name": "CB27",
        "call_value": "AA",
    },
    {
        "variant_name": "2_10600",
        "population_name": "IT82E-18",
        "call_value": "CC",
    },
    {
        "variant_name": "2_10600",
        "population_name": "Suvita 2",
        "call_value": "AA",
    },
    {
        "variant_name": "2_10600",
        "population_name": "IT00K-1263",
        "call_value": "CC",
    },
    {
        "variant_name": "2_10600",
        "population_name": "IT84S-2246",
        "call_value": "CC",
    },
    {
        "variant_name": "2_10600",
        "population_name": "IT93K-503-1",
        "call_value": "CC",
    },
    {
        "variant_name": "2_10600",
        "population_name": "MAGIC001",
        "call_value": "CC",
    },
    {
        "variant_name": "2_10600",
        "population_name": "MAGIC002",
        "call_value": "CC",
    },
    {
        "variant_name": "2_20179",
        "population_name": "IT89KD-288",
        "call_value": "GG",
    },
    {
        "variant_name": "2_20179",
        "population_name": "IT84S-2049",
        "call_value": "GG",
    },
    {
        "variant_name": "2_20179",
        "population_name": "CB27",
        "call_value": "AA",
    },
    {
        "variant_name": "2_20179",
        "population_name": "IT82E-18",
        "call_value": "GG",
    },
    {
        "variant_name": "2_20179",
        "population_name": "Suvita 2",
        "call_value": "GG",
    },
    {
        "variant_name": "2_20179",
        "population_name": "IT00K-1263",
        "call_value": "AA",
    },
    {
        "variant_name": "2_20179",
        "population_name": "IT84S-2246",
        "call_value": "GG",
    },
    {
        "variant_name": "2_20179",
        "population_name": "IT93K-503-1",
        "call_value": "GG",
    },
    {
        "variant_name": "2_20179",
        "population_name": "MAGIC001",
        "call_value": "GG",
    },
    {
        "variant_name": "2_20179",
        "population_name": "MAGIC002",
        "call_value": "AA",
    },
    {
        "variant_name": "2_15967",
        "population_name": "IT89KD-288",
        "call_value": "GG",
    },
    {
        "variant_name": "2_15967",
        "population_name": "IT84S-2049",
        "call_value": "AA",
    },
    {
        "variant_name": "2_15967",
        "population_name": "CB27",
        "call_value": "GG",
    },
    {
        "variant_name": "2_15967",
        "population_name": "IT82E-18",
        "call_value": "GG",
    },
    {
        "variant_name": "2_15967",
        "population_name": "Suvita 2",
        "call_value": "GG",
    },
    {
        "variant_name": "2_15967",
        "population_name": "IT00K-1263",
        "call_value": "GG",
    },
    {
        "variant_name": "2_15967",
        "population_name": "IT84S-2246",
        "call_value": "GG",
    },
    {
        "variant_name": "2_15967",
        "population_name": "IT93K-503-1",
        "call_value": "GG",
    },
    {
        "variant_name": "2_15967",
        "population_name": "MAGIC001",
        "call_value": "GG",
    },
    {
        "variant_name": "2_15967",
        "population_name": "MAGIC002",
        "call_value": "GG",
    },
    {
        "variant_name": "2_50531",
        "population_name": "IT89KD-288",
        "call_value": "AA",
    },
    {
        "variant_name": "2_50531",
        "population_name": "IT84S-2049",
        "call_value": "GG",
    },
    {
        "variant_name": "2_50531",
        "population_name": "CB27",
        "call_value": "AA",
    },
    {
        "variant_name": "2_50531",
        "population_name": "IT82E-18",
        "call_value": "AA",
    },
    {
        "variant_name": "2_50531",
        "population_name": "Suvita 2",
        "call_value": "AA",
    },
    {
        "variant_name": "2_50531",
        "population_name": "IT00K-1263",
        "call_value": "AA",
    },
    {
        "variant_name": "2_50531",
        "population_name": "IT84S-2246",
        "call_value": "AA",
    },
    {
        "variant_name": "2_50531",
        "population_name": "IT93K-503-1",
        "call_value": "AA",
    },
    {
        "variant_name": "2_50531",
        "population_name": "MAGIC001",
        "call_value": "AA",
    },
    {
        "variant_name": "2_50531",
        "population_name": "MAGIC002",
        "call_value": "AA",
    },
    {
        "variant_name": "2_15282",
        "population_name": "IT89KD-288",
        "call_value": "CC",
    },
    {
        "variant_name": "2_15282",
        "population_name": "IT84S-2049",
        "call_value": "CC",
    },
    {
        "variant_name": "2_15282",
        "population_name": "CB27",
        "call_value": "AA",
    },
    {
        "variant_name": "2_15282",
        "population_name": "IT82E-18",
        "call_value": "AA",
    },
    {
        "variant_name": "2_15282",
        "population_name": "Suvita 2",
        "call_value": "CC",
    },
    {
        "variant_name": "2_15282",
        "population_name": "IT00K-1263",
        "call_value": "CC",
    },
    {
        "variant_name": "2_15282",
        "population_name": "IT84S-2246",
        "call_value": "CC",
    },
    {
        "variant_name": "2_15282",
        "population_name": "IT93K-503-1",
        "call_value": "CC",
    },
    {
        "variant_name": "2_15282",
        "population_name": "MAGIC001",
        "call_value": "CC",
    },
    {
        "variant_name": "2_15282",
        "population_name": "MAGIC002",
        "call_value": "CC",
    },
    {
        "variant_name": "2_48268",
        "population_name": "IT89KD-288",
        "call_value": "GG",
    },
    {
        "variant_name": "2_48268",
        "population_name": "IT84S-2049",
        "call_value": "GG",
    },
    {
        "variant_name": "2_48268",
        "population_name": "CB27",
        "call_value": "AA",
    },
    {
        "variant_name": "2_48268",
        "population_name": "IT82E-18",
        "call_value": "GG",
    },
    {
        "variant_name": "2_48268",
        "population_name": "Suvita 2",
        "call_value": "AA",
    },
    {
        "variant_name": "2_48268",
        "population_name": "IT00K-1263",
        "call_value": "GG",
    },
    {
        "variant_name": "2_48268",
        "population_name": "IT84S-2246",
        "call_value": "GG",
    },
    {
        "variant_name": "2_48268",
        "population_name": "IT93K-503-1",
        "call_value": "GG",
    },
    {
        "variant_name": "2_48268",
        "population_name": "MAGIC001",
        "call_value": "GG",
    },
    {
        "variant_name": "2_48268",
        "population_name": "MAGIC002",
        "call_value": "AA",
    },
    {
        "variant_name": "2_46176",
        "population_name": "IT89KD-288",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46176",
        "population_name": "IT84S-2049",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46176",
        "population_name": "CB27",
        "call_value": "AA",
    },
    {
        "variant_name": "2_46176",
        "population_name": "IT82E-18",
        "call_value": "AA",
    },
    {
        "variant_name": "2_46176",
        "population_name": "Suvita 2",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46176",
        "population_name": "IT00K-1263",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46176",
        "population_name": "IT84S-2246",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46176",
        "population_name": "IT93K-503-1",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46176",
        "population_name": "MAGIC001",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46176",
        "population_name": "MAGIC002",
        "call_value": "GG",
    },
    {
        "variant_name": "2_04550",
        "population_name": "IT89KD-288",
        "call_value": "AA",
    },
    {
        "variant_name": "2_04550",
        "population_name": "IT84S-2049",
        "call_value": "GG",
    },
    {
        "variant_name": "2_04550",
        "population_name": "CB27",
        "call_value": "AA",
    },
    {
        "variant_name": "2_04550",
        "population_name": "IT82E-18",
        "call_value": "AA",
    },
    {
        "variant_name": "2_04550",
        "population_name": "Suvita 2",
        "call_value": "AA",
    },
    {
        "variant_name": "2_04550",
        "population_name": "IT00K-1263",
        "call_value": "AA",
    },
    {
        "variant_name": "2_04550",
        "population_name": "IT84S-2246",
        "call_value": "AA",
    },
    {
        "variant_name": "2_04550",
        "population_name": "IT93K-503-1",
        "call_value": "AA",
    },
    {
        "variant_name": "2_04550",
        "population_name": "MAGIC001",
        "call_value": "AA",
    },
    {
        "variant_name": "2_04550",
        "population_name": "MAGIC002",
        "call_value": "AA",
    },
    {
        "variant_name": "2_12293",
        "population_name": "IT89KD-288",
        "call_value": "TT",
    },
    {
        "variant_name": "2_12293",
        "population_name": "IT84S-2049",
        "call_value": "TT",
    },
    {
        "variant_name": "2_12293",
        "population_name": "CB27",
        "call_value": "CC",
    },
    {
        "variant_name": "2_12293",
        "population_name": "IT82E-18",
        "call_value": "TT",
    },
    {
        "variant_name": "2_12293",
        "population_name": "Suvita 2",
        "call_value": "CC",
    },
    {
        "variant_name": "2_12293",
        "population_name": "IT00K-1263",
        "call_value": "TT",
    },
    {
        "variant_name": "2_12293",
        "population_name": "IT84S-2246",
        "call_value": "TT",
    },
    {
        "variant_name": "2_12293",
        "population_name": "IT93K-503-1",
        "call_value": "TT",
    },
    {
        "variant_name": "2_12293",
        "population_name": "MAGIC001",
        "call_value": "TT",
    },
    {
        "variant_name": "2_12293",
        "population_name": "MAGIC002",
        "call_value": "CC",
    },
    {
        "variant_name": "2_15253",
        "population_name": "IT89KD-288",
        "call_value": "AA",
    },
    {
        "variant_name": "2_15253",
        "population_name": "IT84S-2049",
        "call_value": "AA",
    },
    {
        "variant_name": "2_15253",
        "population_name": "CB27",
        "call_value": "AA",
    },
    {
        "variant_name": "2_15253",
        "population_name": "IT82E-18",
        "call_value": "AA",
    },
    {
        "variant_name": "2_15253",
        "population_name": "Suvita 2",
        "call_value": "AA",
    },
    {
        "variant_name": "2_15253",
        "population_name": "IT00K-1263",
        "call_value": "GG",
    },
    {
        "variant_name": "2_15253",
        "population_name": "IT84S-2246",
        "call_value": "GG",
    },
    {
        "variant_name": "2_15253",
        "population_name": "IT93K-503-1",
        "call_value": "AA",
    },
    {
        "variant_name": "2_15253",
        "population_name": "MAGIC001",
        "call_value": "AA",
    },
    {
        "variant_name": "2_15253",
        "population_name": "MAGIC002",
        "call_value": "AA",
    },
    {
        "variant_name": "2_30204",
        "population_name": "IT89KD-288",
        "call_value": "CC",
    },
    {
        "variant_name": "2_30204",
        "population_name": "IT84S-2049",
        "call_value": "CC",
    },
    {
        "variant_name": "2_30204",
        "population_name": "CB27",
        "call_value": "CC",
    },
    {
        "variant_name": "2_30204",
        "population_name": "IT82E-18",
        "call_value": "CC",
    },
    {
        "variant_name": "2_30204",
        "population_name": "Suvita 2",
        "call_value": "CC",
    },
    {
        "variant_name": "2_30204",
        "population_name": "IT00K-1263",
        "call_value": "CC",
    },
    {
        "variant_name": "2_30204",
        "population_name": "IT84S-2246",
        "call_value": "TT",
    },
    {
        "variant_name": "2_30204",
        "population_name": "IT93K-503-1",
        "call_value": "CC",
    },
    {
        "variant_name": "2_30204",
        "population_name": "MAGIC001",
        "call_value": "TT",
    },
    {
        "variant_name": "2_30204",
        "population_name": "MAGIC002",
        "call_value": "CC",
    },
    {
        "variant_name": "2_29305",
        "population_name": "IT89KD-288",
        "call_value": "GG",
    },
    {
        "variant_name": "2_29305",
        "population_name": "IT84S-2049",
        "call_value": "GG",
    },
    {
        "variant_name": "2_29305",
        "population_name": "CB27",
        "call_value": "GG",
    },
    {
        "variant_name": "2_29305",
        "population_name": "IT82E-18",
        "call_value": "AA",
    },
    {
        "variant_name": "2_29305",
        "population_name": "Suvita 2",
        "call_value": "GG",
    },
    {
        "variant_name": "2_29305",
        "population_name": "IT00K-1263",
        "call_value": "AA",
    },
    {
        "variant_name": "2_29305",
        "population_name": "IT84S-2246",
        "call_value": "GG",
    },
    {
        "variant_name": "2_29305",
        "population_name": "IT93K-503-1",
        "call_value": "GG",
    },
    {
        "variant_name": "2_29305",
        "population_name": "MAGIC001",
        "call_value": "GG",
    },
    {
        "variant_name": "2_29305",
        "population_name": "MAGIC002",
        "call_value": "GG",
    },
    {
        "variant_name": "2_33791",
        "population_name": "IT89KD-288",
        "call_value": "TT",
    },
    {
        "variant_name": "2_33791",
        "population_name": "IT84S-2049",
        "call_value": "TT",
    },
    {
        "variant_name": "2_33791",
        "population_name": "CB27",
        "call_value": "TT",
    },
    {
        "variant_name": "2_33791",
        "population_name": "IT82E-18",
        "call_value": "AA",
    },
    {
        "variant_name": "2_33791",
        "population_name": "Suvita 2",
        "call_value": "TT",
    },
    {
        "variant_name": "2_33791",
        "population_name": "IT00K-1263",
        "call_value": "AA",
    },
    {
        "variant_name": "2_33791",
        "population_name": "IT84S-2246",
        "call_value": "TT",
    },
    {
        "variant_name": "2_33791",
        "population_name": "IT93K-503-1",
        "call_value": "TT",
    },
    {
        "variant_name": "2_33791",
        "population_name": "MAGIC001",
        "call_value": "AA",
    },
    {
        "variant_name": "2_33791",
        "population_name": "MAGIC002",
        "call_value": "TT",
    },
    {
        "variant_name": "2_46304",
        "population_name": "IT89KD-288",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46304",
        "population_name": "IT84S-2049",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46304",
        "population_name": "CB27",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46304",
        "population_name": "IT82E-18",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46304",
        "population_name": "Suvita 2",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46304",
        "population_name": "IT00K-1263",
        "call_value": "AA",
    },
    {
        "variant_name": "2_46304",
        "population_name": "IT84S-2246",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46304",
        "population_name": "IT93K-503-1",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46304",
        "population_name": "MAGIC001",
        "call_value": "GG",
    },
    {
        "variant_name": "2_46304",
        "population_name": "MAGIC002",
        "call_value": "GG",
    },
    {
        "variant_name": "2_55108",
        "population_name": "IT89KD-288",
        "call_value": "TT",
    },
    {
        "variant_name": "2_55108",
        "population_name": "IT84S-2049",
        "call_value": "TT",
    },
    {
        "variant_name": "2_55108",
        "population_name": "CB27",
        "call_value": "CC",
    },
    {
        "variant_name": "2_55108",
        "population_name": "IT82E-18",
        "call_value": "TT",
    },
    {
        "variant_name": "2_55108",
        "population_name": "Suvita 2",
        "call_value": "CC",
    },
    {
        "variant_name": "2_55108",
        "population_name": "IT00K-1263",
        "call_value": "TT",
    },
    {
        "variant_name": "2_55108",
        "population_name": "IT84S-2246",
        "call_value": "TT",
    },
    {
        "variant_name": "2_55108",
        "population_name": "IT93K-503-1",
        "call_value": "TT",
    },
    {
        "variant_name": "2_55108",
        "population_name": "MAGIC001",
        "call_value": "TT",
    },
    {
        "variant_name": "2_55108",
        "population_name": "MAGIC002",
        "call_value": "TT",
    },
    {
        "variant_name": "2_32654",
        "population_name": "IT89KD-288",
        "call_value": "TT",
    },
    {
        "variant_name": "2_32654",
        "population_name": "IT84S-2049",
        "call_value": "TT",
    },
    {
        "variant_name": "2_32654",
        "population_name": "CB27",
        "call_value": "TT",
    },
    {
        "variant_name": "2_32654",
        "population_name": "IT82E-18",
        "call_value": "TT",
    },
    {
        "variant_name": "2_32654",
        "population_name": "Suvita 2",
        "call_value": "AA",
    },
    {
        "variant_name": "2_32654",
        "population_name": "IT00K-1263",
        "call_value": "TT",
    },
    {
        "variant_name": "2_32654",
        "population_name": "IT84S-2246",
        "call_value": "TT",
    },
    {
        "variant_name": "2_32654",
        "population_name": "IT93K-503-1",
        "call_value": "TT",
    },
    {
        "variant_name": "2_32654",
        "population_name": "MAGIC001",
        "call_value": "TT",
    },
    {
        "variant_name": "2_32654",
        "population_name": "MAGIC002",
        "call_value": "TT",
    },
]


FIXTURE_GENOTYPE = {
    "genotype_name": "Cowpea_MAGIC_GBS",
    "genotype_info": {
        "platform": "GBS",
        "species": "Vigna unguiculata",
        "population_type": "MAGIC",
        "reference": "tpj13827-sup-0004",
    },
}


FIXTURE_PHENOTYPES = [
    {
        "population_name": "IT89KD-288",
        "trait_name": "Flowering time under full-irrigarion and long-day condition at UCR-CES in 2015 (days)",
        "trait_value": 90.0,
    },
    {
        "population_name": "IT84S-2049",
        "trait_name": "Flowering time under full-irrigarion and long-day condition at UCR-CES in 2015 (days)",
        "trait_value": 54.0,
    },
    {
        "population_name": "CB27",
        "trait_name": "Flowering time under full-irrigarion and long-day condition at UCR-CES in 2015 (days)",
        "trait_value": 45.0,
    },
    {
        "population_name": "IT82E-18",
        "trait_name": "Flowering time under full-irrigarion and long-day condition at UCR-CES in 2015 (days)",
        "trait_value": 50.0,
    },
    {
        "population_name": "Suvita 2",
        "trait_name": "Flowering time under full-irrigarion and long-day condition at UCR-CES in 2015 (days)",
        "trait_value": 58.0,
    },
    {
        "population_name": "IT00K-1263",
        "trait_name": "Flowering time under full-irrigarion and long-day condition at UCR-CES in 2015 (days)",
        "trait_value": 60.0,
    },
    {
        "population_name": "IT84S-2246",
        "trait_name": "Flowering time under full-irrigarion and long-day condition at UCR-CES in 2015 (days)",
        "trait_value": 58.0,
    },
    {
        "population_name": "IT93K-503-1",
        "trait_name": "Flowering time under full-irrigarion and long-day condition at UCR-CES in 2015 (days)",
        "trait_value": 68.0,
    },
    {
        "population_name": "MAGIC001",
        "trait_name": "Flowering time under full-irrigarion and long-day condition at UCR-CES in 2015 (days)",
        "trait_value": 60.0,
    },
    {
        "population_name": "MAGIC002",
        "trait_name": "Flowering time under full-irrigarion and long-day condition at UCR-CES in 2015 (days)",
        "trait_value": 44.0,
    },
]
