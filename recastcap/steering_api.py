#!/usr/bin/env python

import networkx as nx
from networkx.drawing.nx_pydot import write_dot
import json
import adage
import adage.dagutils
import foradage
import logging
import subprocess
import os
import click
import pkg_resources
import cap
import yaml

def run_cap_analysis(workdir,analysis,context_yaml):
    log = logging.getLogger(__name__)
    logging.basicConfig(level = logging.INFO)
    log.info('hello!')

    backend = foradage.RECAST_Backend(2)

    g = adage.mk_dag()

    global_context = yaml.load(open(context_yaml))
    global_context.update(workdir = workdir)

    for k,v in global_context.iteritems():
        candpath = '{}/inputs/{}'.format(workdir,v)
        if os.path.exists(candpath):
            global_context[k] = '/workdir/inputs/{}'.format(v)


    steps_graph = nx.DiGraph()
    workflow = cap.workflow(analysis)

    for step in workflow['stages']:
      steps_graph.add_node(step['name'],step)
      for x in step['dependencies']:
        steps_graph.add_edge(x,step['name'])

    rules = {}
    for stepname in nx.topological_sort(steps_graph):
        stepinfo = steps_graph.node[stepname]
        rule = foradage.RECAST_Rule(stepinfo,workflow,rules,global_context)
        rules[stepname] = rule

    adage.rundag(g,rules.values(), track = True, backend = backend, trackevery = 30, workdir = workdir)

    provgraph = nx.DiGraph()
    for x in nx.topological_sort(g):
      attr = g.node[x].copy()
      attr.update(color = 'red',label = g.getNode(x).name)
      provgraph.add_node(x,attr)
      nodeinfo =  g.getNode(x).task.node

      if 'used_inputs' in nodeinfo:
        for k,inputs_from_node in nodeinfo['used_inputs'].iteritems():
          for one in inputs_from_node:
            depname = 'output_{}_{}_{}'.format(k,one[0],one[1])
            provgraph.add_edge(depname,x)
      else:
        for pre in g.predecessors(x):
          provgraph.add_edge(pre,x)


      for k,v in g.getNode(x).result_of()['RECAST_metadata']['outputs'].iteritems():
        for i,y in enumerate(v):
          name = 'output_{}_{}_{}'.format(g.getNode(x).task.node['name'],k,i)
          provgraph.add_node(name,{'shape':'box','label':'{}_{}'.format(k,i),'color':'blue'})
          provgraph.add_edge(x,name)

    write_dot(provgraph,'{}/adage_workflow_instance.dot'.format(workdir))
    subprocess.call(['dot','-Tpdf','{}/adage_workflow_instance.dot'.format(workdir)], stdout = open('{}/adage_workflow_instance.pdf'.format(workdir),'w'))


    steps_graph_simple = nx.DiGraph()
    for step in workflow['stages']:
      steps_graph_simple.add_node(step['name'])
      for x in step['dependencies']:
        steps_graph_simple.add_edge(x,step['name'])

    write_dot(steps_graph_simple,'{}/adage_steps.dot'.format(workdir))
    subprocess.call(['dot','-Tpdf','{}/adage_steps.dot'.format(workdir)], stdout = open('{}/steps.pdf'.format(workdir),'w'))
  

if __name__ == '__main__':
  main()

