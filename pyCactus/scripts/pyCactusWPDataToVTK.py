#!/usr/bin/env python
# pyCactusWPDataToVTK.py

import os
import glob
import numpy as np

from pyevtk.hl import gridToVTK
from StringIO import StringIO

import xml.etree.cElementTree as ET
import argparse


def convert_wall_tp_to_vts(file_list, output_path):
    print 'output_path: ', output_path
    zts = [] # list containing information related to each zone
    zfs = []   # list containing files related to each zone

    ## start assembling the XML tree for multiblock collection file
    root = ET.Element("VTKFile")
    root.set("type", "Collection")
    collection = ET.SubElement(root, "Collection")
    
    # for each file
    for filenum, file_ in enumerate(file_list):
        # initialize empty list for timestep information
        fnames = []

        with open(file_) as f:
            ## First Pass - find where zones start and get the numbers of variables
            zone_start_lines = []
            vardicts = []

            lines = f.readlines()
            for linenum, line in enumerate(lines):
                # create a blank dictionary
                vardict = {}
                if line.startswith('ZONE'):
                    # cut off the ZONE word and strip whitespace
                    line = line[4:].strip()
                    for a in line.split(','):
                        varname = a.split('=')[0].strip()
                        value   = a.split('=')[1].strip()

                        # add the key/value to the dictionary
                        vardict[varname] = value

                        # append to list of dicts
                        vardicts.append(vardict)

                    # add the line number
                    zone_start_lines.append(linenum)


            # Second Pass - read in the data and write out grid files
            for zone_num, zone_start_line in enumerate(zone_start_lines):
                vardict = vardicts[zone_num]
                nx = int(vardict['I'])
                ny = int(vardict['J'])
                nz = int(vardict['K'])
                solutiontime = float(vardict['SOLUTIONTIME'])
                title = vardict['T']

                if title.startswith('"') and title.endswith('"'):
                    title = title[1:-1]
                
                # load data into numpy array
                X = np.genfromtxt(StringIO(lines[zone_start_line+1])).reshape([nz,ny,nx])
                Y = np.genfromtxt(StringIO(lines[zone_start_line+2])).reshape([nz,ny,nx])
                Z = np.genfromtxt(StringIO(lines[zone_start_line+3])).reshape([nz,ny,nx])
                sigma = np.genfromtxt(StringIO(lines[zone_start_line+4])).reshape([1,ny-1,nx-1])

                # set the data filename and write to .vts file
                name = "WPData_zone" + str(zone_num) + "_t" + str(filenum)
                data_filename = gridToVTK(output_path + '/' + name, X, Y, Z, cellData={"sigma" : sigma})
                
                fnames.append(os.path.basename(data_filename))

            # append data
            zfs.append(fnames)
            zts.append(solutiontime)

    num_zones = len(zone_start_lines)

    ## Write to VTS and PVD files
    for iz in range(num_zones):
        root = ET.Element("VTKFile")
        root.set("type", "Collection")
        collection = ET.SubElement(root, "Collection")
        
        for it,time in enumerate(zts):
            # add elements to XML tree for PVD collection file
            dataset = ET.SubElement(collection, "DataSet")
            dataset.set("timestep", str(time))
            dataset.set("file", os.path.basename(zfs[it][iz]))
        
        # write the collection files
        tree = ET.ElementTree(root)
        pvd_filename = os.path.abspath(output_path + '/' + 'WPData_zone' + str(iz) + '.pvd')
        tree.write(pvd_filename, xml_declaration=True)
        print 'Wrote ParaView collection file: ' + pvd_filename


if __name__ == '__main__':

    # parse command line arguments
    parser = argparse.ArgumentParser(description="""Convert CACTUS wall data files from TecPlot structured to VTK.
    The wall data is moved to '/WallVTK'
    Expects that the wall data filenames match the patterns:
    [case_name]_WPData_*.tp""")


    parser = argparse.ArgumentParser()
    parser.add_argument("case_path", help="path to TP files to be converted.", type=str)
    parser.add_argument("case_name", help="prefix of output files, e.g. [case_name]_WakeData_1.csv", type=str)
    parser.add_argument("output_path", help="desired output path for VTK files.", type=str)
    
    args = parser.parse_args()

    # read in command-line arguments
    case_path   = args.case_path
    case_name   = args.case_name
    output_path = args.output_path

    wall_out_path = os.path.abspath(output_path + '/WallVTK')

    # make directories
    if not os.path.exists(wall_out_path):
        try:
            os.makedirs(wall_out_path)
        except:
            print 'There was an error creating the directory' + wall_out_path

    # find the .tp files
    file_list = glob.glob('*WPData_*.tp')
    print wall_out_path

    # call the converter function
    convert_wall_tp_to_vts(file_list, wall_out_path)