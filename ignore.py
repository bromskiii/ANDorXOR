import requests
import xml.etree.ElementTree as ET

CSW_URL = "https://portal.opentopography.org/geoportal/csw/discovery"

xml = """<csw:GetRecords xmlns:csw="http://www.opengis.net/cat/csw/2.0.2"
  xmlns:ogc="http://www.opengis.net/ogc" xmlns:gml="http://www.opengis.net/gml"
  version="2.0.2" service="CSW" resultType="results" startPosition="1" maxRecords="10"
  outputSchema="http://www.isotc211.org/2005/gmd">
  <csw:Query typeNames="csw:Record">
    <csw:ElementSetName>full</csw:ElementSetName>
    <csw:Constraint version="1.1.0">
      <ogc:Filter>
        <ogc:BBOX>
          <ogc:PropertyName>ows:BoundingBox</ogc:PropertyName>
          <gml:Envelope>
            <gml:lowerCorner>-79.80 43.68</gml:lowerCorner>
            <gml:upperCorner>-79.73 43.73</gml:upperCorner>
          </gml:Envelope>
        </ogc:BBOX>
      </ogc:Filter>
    </csw:Constraint>
  </csw:Query>
</csw:GetRecords>"""

r = requests.post(CSW_URL, data=xml, headers={"Content-Type": "application/xml"})
r.raise_for_status()

root = ET.fromstring(r.content)
ns = {
    'dc': 'http://purl.org/dc/elements/1.1/',
    'ows': 'http://www.opengis.net/ows',
    'gmd': 'http://www.isotc211.org/2005/gmd',
    'csw': 'http://www.opengis.net/cat/csw/2.0.2'
}

# example: list record titles and identifiers
for rec in root.findall('.//{http://purl.org/dc/elements/1.1/}title'):
    print("Title:", rec.text)

for fid in root.findall('.//{http://purl.org/dc/elements/1.1/}identifier'):
    print("ID:", fid.text)

# find envelopes
for env in root.findall('.//{http://www.opengis.net/ows}Envelope'):
    low = env.find('{http://www.opengis.net/gml}LowerCorner')
    up = env.find('{http://www.opengis.net/gml}UpperCorner')
    print("Envelope:", (low.text if low is not None else ""), (up.text if up is not None else ""))
