#!/usr/bin/python2.7

import graph_tool.all as gt

import pandas as pd

print "Loading..."

g = gt.load_graph_from_csv('links.tsv', string_vals=True, csv_options={"delimiter":'\t'})

tags = pd.read_csv('tags.tsv', '\t', header=None, names=['pname','tags'])
tags.dropna(inplace=True)
tags.tags = tags.tags.apply(lambda x: x.split(',')[:-1])
tags.set_index('pname', inplace=True)


print "Classifying..."

g.vp.cat = g.new_vertex_property("string")
disp_name = g.new_vertex_property("string")
fill_color = g.new_vertex_property("vector<float>")

for v in g.vertices():
	t = tags.tags.get(g.vp.name[v], [])
	disp_name[v] = g.vp.name[v][:10]

	if not {"admin", "template",  "essay", "guide", "workbench",
			"fragment", "sandbox", "project"}.isdisjoint(t) or ":" in g.vp.name[v]:
		g.vp.cat[v] = "system"
		fill_color[v] = [0.,0.,0.,1.]
	elif not {"hub", "news", "author"}.isdisjoint(t):
		g.vp.cat[v] = "hub"
		fill_color[v] = [1.,1.,1.,1.]
	elif not {"scp", "safe", "euclid", "keter", "thaumiel", "unclassed"}.isdisjoint(t):
		g.vp.cat[v] = "scp"
		fill_color[v] = [1.,0.,0.,1.]
	elif "goi-format" in t or "tale" in t:
		g.vp.cat[v] = "story"
		fill_color[v] = [0.,1.,0.,1.]
	elif not {"supplement", "experiment", "exploration", "incident", "interview",
			"splash", "artwork", "scp-fuel", "archived", "joke"}.isdisjoint(t):
		g.vp.cat[v] = "extra"
		fill_color[v] = [0.,0.,1.,1.]
	else:
		g.vp.cat[v] = "system"
		fill_color[v] = [0.,0.,0.,1.]


print "Pruning..."

g.remove_vertex(gt.find_vertex(g, g.vp.cat, "system"), fast=True)
g.remove_vertex(gt.find_vertex(g, g.vp.cat, "hub"), fast=True)
# g.remove_vertex(gt.find_vertex(g, g.vp.cat, "story"), fast=True)
# g.remove_vertex(gt.find_vertex(g, g.vp.cat, "extra"), fast=True)
#g.remove_vertex(gt.find_vertex_range(g, "out", (26,999)))
#g.remove_vertex(gt.find_vertex_range(g, "in", (7,999)))

print "Laying out..."

# layout = gt.sfdp_layout(g)

print "Plotting..."

# gt.graph_draw(g, pos=layout, vprops={"fill_color":fill_color, "text":disp_name, "text_position":0, "font_size":9, "anchor":0},output_size=(1600,1200))

# gt.graph_draw(g, pos=layout, vprops={"fill_color":fill_color, "text":disp_name, "text_position":-2, "font_size":9, "text_color":"black"}, bg_color="white", output_size=(10000,10000), output="scp-wiki.png")