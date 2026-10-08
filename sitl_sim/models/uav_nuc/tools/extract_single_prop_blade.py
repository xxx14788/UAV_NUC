#!/usr/bin/env python3
"""Extract the +X blade from PX4's two-blade Iris COLLADA propeller."""

import argparse
import xml.etree.ElementTree as ET


NS = {"c": "http://www.collada.org/2005/11/COLLADASchema"}
ET.register_namespace("", NS["c"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument("--root-cut", type=float, default=0.006,
                        help="keep faces whose position centroid x exceeds this value")
    args = parser.parse_args()

    tree = ET.parse(args.source)
    root = tree.getroot()
    mesh = root.find(".//c:library_geometries/c:geometry/c:mesh", NS)
    polylist = mesh.find("c:polylist", NS)
    inputs = polylist.findall("c:input", NS)
    stride = max(int(item.get("offset", "0")) for item in inputs) + 1

    vertex_input = next(item for item in inputs if item.get("semantic") == "VERTEX")
    position_offset = int(vertex_input.get("offset", "0"))
    vertices_id = vertex_input.get("source").lstrip("#")
    vertices = mesh.find("c:vertices[@id='%s']" % vertices_id, NS)
    position_source_id = next(
        item.get("source").lstrip("#") for item in vertices.findall("c:input", NS)
        if item.get("semantic") == "POSITION"
    )
    position_source = mesh.find("c:source[@id='%s']" % position_source_id, NS)
    floats = [float(value) for value in position_source.find("c:float_array", NS).text.split()]
    accessor = position_source.find("c:technique_common/c:accessor", NS)
    position_stride = int(accessor.get("stride", "3"))

    vcounts = [int(value) for value in polylist.find("c:vcount", NS).text.split()]
    indices = [int(value) for value in polylist.find("c:p", NS).text.split()]
    kept_vcounts = []
    kept_indices = []
    cursor = 0

    for vertex_count in vcounts:
        face_size = vertex_count * stride
        face = indices[cursor:cursor + face_size]
        cursor += face_size
        position_indices = [
            face[vertex * stride + position_offset] for vertex in range(vertex_count)
        ]
        centroid_x = sum(floats[index * position_stride] for index in position_indices) / vertex_count
        if centroid_x > args.root_cut:
            kept_vcounts.append(vertex_count)
            kept_indices.extend(face)

    if not kept_vcounts:
        raise SystemExit("no blade faces selected")

    polylist.set("count", str(len(kept_vcounts)))
    polylist.find("c:vcount", NS).text = " ".join(map(str, kept_vcounts))
    polylist.find("c:p", NS).text = " ".join(map(str, kept_indices))
    tree.write(args.output, encoding="utf-8", xml_declaration=True)
    print("%s: kept %d of %d faces" % (args.output, len(kept_vcounts), len(vcounts)))


if __name__ == "__main__":
    main()
