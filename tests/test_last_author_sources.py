import unittest
import xml.etree.ElementTree as ET

from neurodaily.sources import arxiv, biorxiv, europe_pmc, openalex, pubmed


KEY = "last_author_affiliations"


class LastAuthorSourceTests(unittest.TestCase):
    def test_pubmed_uses_last_persons_own_nested_affiliations(self):
        item = _pubmed('''
            <Author><LastName>Chen</LastName><ForeName>P</ForeName>
                <AffiliationInfo><Affiliation>First Institute, Canada</Affiliation></AffiliationInfo>
            </Author>
            <Author><LastName>Andersson</LastName><ForeName>A</ForeName>
                <AffiliationInfo><Affiliation><i>First Lab</i>, Sweden</Affiliation>
                    <Identifier Source="ROR">https://ror.org/0022wn503</Identifier></AffiliationInfo>
                <AffiliationInfo><Affiliation>Second Lab, Denmark</Affiliation></AffiliationInfo>
            </Author>
        ''')
        self.assertEqual(item.authors, ["P Chen", "A Andersson"])
        self.assertEqual(item.affiliations,
                         ["First Institute, Canada", "First Lab, Sweden", "Second Lab, Denmark"])
        self.assertEqual(item.extra[KEY], [
            {"address": "First Lab, Sweden", "institution_id": "https://ror.org/0022wn503"},
            {"address": "Second Lab, Denmark"},
        ])

    def test_pubmed_skips_unaffiliated_collective_and_incomplete_last_names(self):
        person = ('<Author><LastName>Chen</LastName><AffiliationInfo><Affiliation>First Institute, Canada'
                  '</Affiliation></AffiliationInfo></Author>')
        for last, attrs in [
            ("<Author><LastName>Snow</LastName></Author>", ""),
            ("<Author><CollectiveName>Research Consortium</CollectiveName></Author>", ""),
            ("", 'CompleteYN="N"'),
        ]:
            with self.subTest(last=last, attrs=attrs):
                self.assertNotIn(KEY, _pubmed(person + last, attrs).extra)

    def test_europe_pmc_uses_last_structured_author_and_keeps_explicit_ror(self):
        rows = [
            {"fullName": "Chen E", "lastName": "Chen", "affiliation": "First Institute, Canada"},
            {"fullName": "Rossi L", "lastName": "Rossi", "affiliation": "Public Health Lab, Italy",
             "authorAffiliationDetailsList": {"authorAffiliation": [
                 {"affiliation": "Public Health Lab, Italy", "affiliationOrgId": "ror.org/02catss52"},
                 {"affiliation": "Research Center, France", "affiliationOrgId": "grid.1234.0"},
             ]}},
        ]
        self.assertEqual(_europe(rows).extra[KEY], [
            {"address": "Public Health Lab, Italy", "institution_id": "ror.org/02catss52"},
            {"address": "Research Center, France"},
        ])
        self.assertNotIn(KEY, _europe([*rows, {"fullName": "A Consortium", "collectiveName": "A Consortium",
                                              "affiliation": "University, Japan"}]).extra)
        self.assertNotIn(KEY, _europe([*rows, None]).extra)

    def test_openalex_uses_explicit_raw_address_links_for_country_and_ror(self):
        item = _openalex([
            {"author": {"display_name": "Erica Chen"}, "author_position": "first",
             "raw_affiliation_strings": ["First Institute, Canada"]},
            {"author": {"display_name": "Luisa Rossi"}, "author_position": "last",
             "raw_affiliation_strings": ["Unit A", "Unit B", "Unresolved Institution"],
             "countries": ["GB", "FR", "IT"],
             "institutions": [
                 {"id": "https://openalex.org/I11", "display_name": "Institut B", "country_code": "FR"},
                 {"id": "https://openalex.org/I22", "display_name": "Istituto A", "country_code": "IT",
                  "ror": "https://ror.org/0292tjy16"},
             ], "affiliations": [
                 {"raw_affiliation_string": "Unit A", "institution_ids": ["https://openalex.org/I22"]},
                 {"raw_affiliation_string": "Unit B", "institution_ids": ["https://openalex.org/I11"]},
             ]},
        ])
        self.assertEqual(item.extra[KEY], [
            {"address": "Unit A", "country": "IT", "institution_id": "https://ror.org/0292tjy16"},
            {"address": "Unit B", "country": "FR"},
            {"address": "Unresolved Institution"},
        ])
        self.assertEqual(item.affiliations[0], "First Institute, Canada")

    def test_openalex_keeps_matched_institution_and_rejects_truncated_byline(self):
        author = {"author": {"display_name": "Luisa Rossi"}, "author_position": "first",
                  "institutions": [{"display_name": "Istituto A", "country_code": "IT"}]}
        self.assertEqual(_openalex([author]).extra[KEY], [{"address": "Istituto A", "country": "IT"}])
        self.assertNotIn(KEY, _openalex([author], is_authors_truncated=True).extra)
        self.assertNotIn(KEY, _openalex([author], authors_count=2).extra)
        self.assertNotIn(KEY, _openalex([author, author]).extra)
        self.assertNotIn(KEY, _openalex([author, None]).extra)
        self.assertNotIn(KEY, _openalex([{**author, "raw_author_name": "A Study Consortium"}]).extra)

    def test_arxiv_uses_affiliation_in_the_author_namespace(self):
        first = '<author><name>First Person</name><a:affiliation>First Institute</a:affiliation></author>'
        last = ('<author><name>Last Person</name><a:affiliation>Last Institute</a:affiliation>'
                '<a:affiliation>Other Institute</a:affiliation></author>')
        item = _arxiv(first + last)
        self.assertEqual(item.affiliations, ["First Institute", "Last Institute", "Other Institute"])
        self.assertEqual(item.extra[KEY], [{"address": "Last Institute"}, {"address": "Other Institute"}])
        self.assertNotIn(KEY, _arxiv(first + "<author><name>Last Person</name></author>").extra)
        self.assertNotIn(KEY, _arxiv(first + '<author><a:affiliation>Unnamed</a:affiliation></author>').extra)
        self.assertNotIn(KEY, _arxiv(first + last.replace("Last Person", "Physics Collaboration")).extra)

    def test_biorxiv_requires_unique_corresponding_author_to_be_last(self):
        byline = "Erica Chen; Luisa Rossi"
        self.assertEqual(_preprint(byline, "Rossi, Luisa").extra[KEY], [{"address": "Research Institute"}])
        self.assertNotIn(KEY, _preprint(byline, "Erica Chen").extra)
        self.assertNotIn(KEY, _preprint(byline, "L. Rossi").extra)
        self.assertNotIn(KEY, _preprint("Luisa Rossi; Luisa Rossi", "Luisa Rossi").extra)
        self.assertNotIn(KEY, _preprint("Luisa Rossi; A Study Consortium", "A Study Consortium").extra)
        self.assertEqual(_preprint(byline, "Erica Chen").affiliations, ["Research Institute"])

    def test_biorxiv_matches_provider_initials_only_if_unique(self):
        item = _preprint("Chen, E.; Rossi, L. S.", "Luisa Sarah Rossi")
        self.assertEqual(item.extra[KEY], [{"address": "Research Institute"}])
        self.assertNotIn(KEY, _preprint("Rossi, L. S.; Rossi, L. S.", "Luisa Sarah Rossi").extra)
        self.assertNotIn(KEY, _preprint("Luisa Sarah Rossi; Rossi, L. S.", "Luisa Sarah Rossi").extra)
        self.assertNotIn(KEY, _preprint("Chen, E.; Rossi, L. J.", "Luisa Sarah Rossi").extra)


def _pubmed(authors, attrs=""):
    entry = ET.fromstring(f'''
        <PubmedArticle><MedlineCitation><PMID>1</PMID><Article>
            <ArticleTitle>A publication</ArticleTitle><AuthorList {attrs}>{authors}</AuthorList>
        </Article></MedlineCitation></PubmedArticle>
    ''')
    return pubmed._parse_article(entry)


def _europe(authors):
    return europe_pmc._paper({"title": "A publication", "id": "1", "source": "MED",
                              "authorList": {"author": authors}})


def _openalex(authors, **fields):
    return openalex._paper({"display_name": "A publication", "id": "https://openalex.org/W1",
                            "authorships": authors, **fields})


def _arxiv(authors):
    entry = ET.fromstring(f'''
        <entry xmlns="http://www.w3.org/2005/Atom" xmlns:a="http://arxiv.org/schemas/atom">
            <title>A publication</title><id>https://arxiv.org/abs/2401.00001</id>{authors}
        </entry>
    ''')
    return arxiv._parse_entry(entry)


def _preprint(authors, corresponding):
    return biorxiv._item("biorxiv", {"authors": authors, "author_corresponding": corresponding,
                                    "author_corresponding_institution": "Research Institute"},
                         "A publication", "", "10.1101/fixture", "")
