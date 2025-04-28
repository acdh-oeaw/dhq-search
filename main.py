import glob
import os
import typesense

from acdh_tei_pyutils.tei import TeiReader
from acdh_tei_pyutils.utils import extract_fulltext
from tqdm import tqdm
from typesense.exceptions import ObjectNotFound


TYPESENSE_API_KEY = os.environ.get("TYPESENSE_API_KEY", "xyz")
TYPESENSE_TIMEOUT = os.environ.get("TYPESENSE_TIMEOUT", "120")
TYPESENSE_HOST = os.environ.get("TYPESENSE_HOST", "typesense.acdh-dev.oeaw.ac.at")
TYPESENSE_PORT = os.environ.get("TYPESENSE_PORT", "443")
TYPESENSE_PROTOCOL = os.environ.get("TYPESENSE_PROTOCOL", "https")
client = typesense.Client(
    {
        "nodes": [
            {
                "host": TYPESENSE_HOST,
                "port": TYPESENSE_PORT,
                "protocol": TYPESENSE_PROTOCOL,
            }
        ],
        "api_key": TYPESENSE_API_KEY,
        "connection_timeout_seconds": int(TYPESENSE_TIMEOUT),
    }
)
URL_PATTERN = "https://digitalhumanities.org/dhq/vol/{}/{}/{}/{}.html"
COLLECTION_NAME = "dhq-search"
TAG_BLACKLIST = ["{http://www.tei-c.org/ns/1.0}abbr"]


try:
    client.collections[COLLECTION_NAME].delete()
except ObjectNotFound:
    pass

current_schema = {
    "name": COLLECTION_NAME,
    "enable_nested_fields": True,
    "fields": [
        {"name": "id", "type": "string", "sort": True},
        {"name": "url", "type": "string", "sort": True},
        {"name": "title", "type": "string", "sort": True},
        {"name": "full_text", "type": "string", "sort": True},
        {"name": "volume", "type": "string", "facet": True, "sort": True},
        {"name": "issue", "type": "string", "facet": True, "sort": True},
        {"name": "license", "type": "string", "facet": True, "sort": True},
        {"name": "keywords", "type": "string[]", "optional": True, "facet": True},
    ],
}

client.collections.create(current_schema)


files = [x for x in glob.glob("dhq-journal/articles/00*/00*.xml") if "_" not in x]
records = []
for x in tqdm(files):
    try:
        doc = TeiReader(x)
    except:  # noqa
        continue
    article_id = doc.any_xpath(".//tei:idno[@type='DHQarticle-id']")[0].text
    volume = doc.any_xpath(".//tei:idno[@type='volume']")[0].text
    issue = doc.any_xpath(".//tei:idno[@type='issue']")[0].text
    try:
        license = doc.any_xpath(".//tei:availability/@status")[0]
    except IndexError:
        license = "no license provided"
    try:
        title = extract_fulltext(doc.any_xpath(".//tei:title[@type='article']")[0])
    except Exception:
        try:
            extract_fulltext(doc.any_xpath(".//tei:title")[0])
        except:  # noqa
            continue
    keywords = []
    for x in doc.any_xpath(".//tei:term[@corresp]/@corresp"):
        keywords.append(x[1:].replace("_", " "))
    if article_id and volume and issue:
        url = URL_PATTERN.format(volume, issue, article_id, article_id)
        body = doc.any_xpath(".//tei:text")[0]
        full_text = extract_fulltext(body, tag_blacklist=TAG_BLACKLIST) + title
        records.append(
            {
                "id": article_id,
                "url": url,
                "title": title,
                "volume": volume,
                "issue": issue,
                "license": license,
                "keywords": keywords,
                "full_text": full_text,
            }
        )

make_index = client.collections[COLLECTION_NAME].documents.import_(records)
print(make_index)
print(f"done with indexing {COLLECTION_NAME}")
