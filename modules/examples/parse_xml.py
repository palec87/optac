
import xml.etree.ElementTree as ET

mytree = ET.parse('device.xml')
myroot = mytree.getroot()
for x in myroot.findall('device/videoformat'):
    print(x.text, type(x.text))
format = x.text.split()[0]
print(format)


