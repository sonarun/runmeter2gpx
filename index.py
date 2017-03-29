import sqlite3
from datetime import datetime, timedelta
from xml.etree.ElementTree import Element, SubElement, dump

from xml.etree import ElementTree
from xml.dom import minidom

def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ", encoding="UTF-8")


# Connect to the Database
conn = sqlite3.connect('Meter.db')
# We have to build separate cursors for each time we iterate the cursor
c = conn.cursor()
c2 = conn.cursor()
c3 = conn.cursor()

# Counting the total amount of runs
count = 0

# GPX files use a link and an e-mail for a person
linkhref = 'http://www.google.com'
linktext = 'Google'

# Get the name of the person from the register
c.execute('SELECT emailAddr, firstName, lastName FROM register WHERE rowid = 1')
emailAddr, firstName, lastName = c.fetchone()

fullName = firstName + ' ' + lastName

# Split the e-mail address into ID and Domain
emailid = emailAddr.split("@")[0]
emaildomain = emailAddr.split("@")[1]


# Now we start iterating over all of the runs
# Get the run information for each run
c.execute('SELECT runID, startTime FROM run')
for row in c:
    runID = row[0]
    startTime = row[1]

    # Lets count how many runs there are
    count +=1

    # Get the startTime, which is already in UTC and remove the microseconds
    startTime = datetime.strptime(startTime, '%Y-%m-%d %H:%M:%S.%f').replace(microsecond=0)

    # Get replace the newly formed datetime object with the ISO formatted string, the Z needs to be added since python's isoformat string doesn't include it
    startTimeISOFormatted = startTime.isoformat() + 'Z'

    filename = "run-" + startTime.strftime('%Y%m%d-%H-%M') + ".gpx"

    # Form the XML
    gpx = Element("gpx", {
      'version': "1.1",
      'creator': "Runmeter - http://www.runmeter.com",
      'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance",
      'xmlns:abvio': "http://www.abvio.com/xmlschemas/1",
      'xmlns:gpxtpx': "http://www.garmin.com/xmlschemas/TrackPointExtension/v1",
      'xmlns': "http://www.topografix.com/GPX/1/1",
      'xsi:schemaLocation': "http://www.topografix.com/GPX/1/1 http://www.topografix.com/gpx/1/1/gpx.xsd",
      })

    gpx_metadata = SubElement(gpx, "metadata")


    gpx_metadata_name = SubElement(gpx_metadata, "name")
    gpx_metadata_name.text = filename

    gpx_metadata_desc = SubElement(gpx_metadata, "desc")
    gpx_metadata_desc.text = "Runmeter run on " + startTime.strftime('%A, %B %d, %Y')

    gpx_metadata_author = SubElement(gpx_metadata, "author")
    gpx_metadata_author_name = SubElement(gpx_metadata_author, "name")
    gpx_metadata_author_name.text=fullName
    gpx_metadata_author_email = SubElement(gpx_metadata_author, "email", {
        'id': emailid,
        'domain': emaildomain,
        })
    gpx_metadata_author_link = SubElement(gpx_metadata_author, "link", {
        'href': 'http://www.runmeter.com',
        })
    gpx_metadata_author_link_text = SubElement(gpx_metadata_author_link, "text")
    gpx_metadata_author_link_text.text = "Abvio Runmeter"
    gpx_metadata_time = SubElement(gpx_metadata, "time")
    gpx_metadata_time.text = startTimeISOFormatted
    gpx_metadata_keywords = SubElement(gpx_metadata, "keywords")
    gpx_metadata_keywords.text = "Runmeter, Run"

    c2.execute('SELECT min(latitude) FROM coordinate WHERE runID = (?)', [runID])
    minlat = c2.fetchone()
    c2.execute('SELECT max(latitude) FROM coordinate WHERE runID = (?)', [runID])
    maxlat = c2.fetchone()
    c2.execute('SELECT min(longitude) FROM coordinate WHERE runID = (?)', [runID])
    minlon = c2.fetchone()
    c2.execute('SELECT max(longitude) FROM coordinate WHERE runID = (?)', [runID])
    maxlon = c2.fetchone()
    gpx_metadata_bounds = SubElement(gpx_metadata, "bounds", {
        'minlat': str(minlat[0]),
        'maxlat': str(maxlat[0]),
        'minlon': str(minlon[0]),
        'maxlon': str(maxlon[0]),
        })

    gpx_trk = SubElement(gpx, "trk")
    gpx_trk_src = SubElement(gpx_trk, "src")
    gpx_trk_src.text = "Logged by " + fullName + " using Runmeter"
    gpx_trk_link = SubElement(gpx_trk, "link", {
        'href': linkhref
        })
    gpx_trk_link_text = SubElement(gpx_trk_link, "text")
    gpx_trk_link_text.text = linktext
    gpx_trk_trkseg = SubElement(gpx_trk, "trkseg")

    c3.execute('SELECT latitude, longitude, timeOffset FROM coordinate WHERE runID = (?)', [runID])
    for row in c3:
        latitude = row[0]
        longitude = row[1]

        # Get the time offset and round seconds 2 two decimal places
        timeOffset = round(row[2],2)
        # Add the seconds to the start time to get the delta from start of run
        timeOffset = startTime + timedelta(seconds=timeOffset)
        # Remove the microseconds from the datetime object
        timeOffset = timeOffset.replace(microsecond=0)
        #format the string to ISO
        timeOffsetISOFormatted = timeOffset.isoformat() + 'Z'

        gpx_trk_trkseg_trkpt = SubElement(gpx_trk_trkseg, "trkpt", {
            'lat': str(latitude),
            'lon': str(longitude),
            })
        # I can't seem to find the elevation in the Meter.db, defaulting to 0, it's optional.
        gpx_trk_trkseg_trkpt_ele = SubElement(gpx_trk_trkseg_trkpt, "ele")
        gpx_trk_trkseg_trkpt_ele.text = '0'
        gpx_trk_trkseg_trkpt_time = SubElement(gpx_trk_trkseg_trkpt, "time")
        gpx_trk_trkseg_trkpt_time.text = timeOffsetISOFormatted

    # Write to file
    f = open(filename, "w")
    f.write (prettify(gpx))

print("Wrote %s runs to file." % (count))
