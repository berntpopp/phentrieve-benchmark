from xml.etree.ElementTree import Element, SubElement, tostring

XMI = "http://www.omg.org/XMI"
CAS = "http:///uima/cas.ecore"
SEGMENTATION = "http:///de/tudarmstadt/ukp/dkpro/core/api/segmentation/type.ecore"
CUSTOM = "http:///webanno/custom.ecore"


def synthetic_e3c_xmi(*, unknown_custom_type: bool = False) -> bytes:
    root = Element(f"{{{XMI}}}XMI", {f"{{{XMI}}}version": "2.0"})
    SubElement(root, f"{{{CAS}}}NULL", {f"{{{XMI}}}id": "0"})
    text = "A😀 Cafe\u0301\r\nfinal\r\n"
    SubElement(
        root,
        f"{{{CAS}}}Sofa",
        {
            f"{{{XMI}}}id": "1",
            "sofaString": text,
            "sofaID": "_InitialView",
        },
    )
    for number, name in enumerate(("Token", "Sentence"), start=2):
        SubElement(
            root,
            f"{{{SEGMENTATION}}}{name}",
            {
                f"{{{XMI}}}id": str(number),
                "sofa": "1",
                "begin": "4",
                "end": "9",
            },
        )
    SubElement(
        root,
        f"{{{CUSTOM}}}METADATA",
        {
            f"{{{XMI}}}id": "4",
            "sofa": "1",
            "begin": "0",
            "end": "0",
            "docLanguage": "x-unspecified",
        },
    )
    entities = ("CLINENTITY", "EVENT", "ACTOR", "BODYPART", "TIMEX3", "RML")
    for number, name in enumerate(entities, start=100):
        attributes = {
            f"{{{XMI}}}id": str(number),
            "sofa": "1",
            "begin": "4",
            "end": "9",
        }
        if name == "CLINENTITY":
            attributes["entityID"] = "C1234567"
            attributes["discontinuous"] = "false"
        if name == "EVENT":
            attributes["polarity"] = "POS"
        SubElement(root, f"{{{CUSTOM}}}{name}", attributes)
    relations = (
        "TIMEX3TimexLinkLink",
        "RMLPERTAINSTOLink",
        "EVENTTLINKLink",
        "EVENTALINKLink",
    )
    for number, name in enumerate(relations, start=200):
        SubElement(
            root,
            f"{{{CUSTOM}}}{name}",
            {
                f"{{{XMI}}}id": str(number),
                "role": "source",
                "target": "100",
            },
        )
    if unknown_custom_type:
        SubElement(root, f"{{{CUSTOM}}}Unexpected", {f"{{{XMI}}}id": "999"})
    return tostring(root, encoding="utf-8", xml_declaration=True)
