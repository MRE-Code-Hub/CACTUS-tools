import os
import time as tmod

import numpy as np
import pandas as pd

from warnings import *

class CactusField():
	"""Class for reading WakeData (element) from CSV files.

	Grid node locations X,Y,Z are assumed to be the same for all timesteps.

	Attributes
	----------
	filenames : list
		Filenames (str) of wake element data files.
	num_times : int
		Number of timesteps of wake element data.
	times : list
		List of times (float) of wake element data.
	fdict : dict
		A dictionary of `{time : filename}`.
	nx : int
		Number of grid points in x direction.
	ny : int
		Number of grid points in y direction.
	nz : int
		Number of grid points in z direction.
	dx : float
		Grid spacing in x direction.
	dy : float
		Grid spacing in y direction.
	dz : float
		Grid spacing in z direction.
	xlim : list
		Extents of grid in x direction, [x_min, x_max].
	ylim : list
		Extents of grid in x direction, [y_min, y_max].
	zlim : list
		Extents of grid in x direction, [z_min, z_max].
	"""

	def __init__(self, filenames):
		"""Initializes the instance, reads in the headers from each file."""
		self.filenames = filenames
		self.num_times = len(filenames)
		self.times = []
		
		# dictionary of time : filename
		self.fdict = {}

		# get the times for each timestep
		# the name of the column containing time info
		time_col_name = 'Normalized Time (-)'
	
		for fname in filenames:
			time = get_file_time(fname, time_col_name)
			self.times.append(time)
			self.fdict[time] = fname

		# sort the times
		self.times = np.sort(np.array(self.times))

		# get grid dimensions by reading the first file
		# (note that this isn't necessarily the FIRST timestep, just the first file from glob)
		df = load_data(filenames[0])
		_, grid_dims = self.fielddata_from_df(df)

		# unpack grid dimensions, save to instance variable
		self.grid_dims = grid_dims


	def get_df_inst(self, time=None, fname=None):
		"""Gets the data from a specified time or filename.

		Either the time or the filename must be specified.

		Parameters
		----------
		time : Optional[float]
		    The time at which to extract the dataframe.
		fname : Optional[str]
		    The filename to read (defaults to self.fdict[time]).

		Returns
		-------
		df_inst : pandas.DataFrame
		    DataFrame of the time.
		"""

		if (time is None) and (fname is None):
			 print 'Error: must specify either the time or filename of the desired data.'

		if time is not None:
			# if the time is specified, get the filename
			fname = self.fdict[time]
		else:
			# otherwise, use the filename given
			pass

		# read the CSV data file
		df_inst = load_data(fname)

		return df_inst

	
	def fielddata_from_df(self, df):
		"""Takes a dataframe containing field data at a single timestep and
		returns a dictionary of the data as np.arrays.

		NumPy arrays are keyed by a descriptive variable name.

		Parameters
		----------
		df : pandas.DataFrame

		Returns
		-------
		grid_data : dict
			Dictionary of np.arrays containing the data.
		grid_dims : dict
			Dictionary of grid dimensions.
		"""
		# column names
		time_col_name = 'Normalized Time (-)'
		x_col_name    = 'X/R (-)'
		y_col_name    = 'Y/R (-)'
		z_col_name    = 'Z/R (-)'
		u_col_name    = 'U/Uinf (-)'
		v_col_name    = 'V/Uinf (-)'
		w_col_name    = 'W/Uinf (-)'
		ufs_col_name  = 'Ufs/Uinf (-)'
		vfs_col_name  = 'Vfs/Uinf (-)'
		wfs_col_name  = 'Wfs/Uinf (-)'

		# extract columns
		x   = df.loc[:,x_col_name]
		y   = df.loc[:,y_col_name].values
		z   = df.loc[:,z_col_name].values
		u   = df.loc[:,u_col_name].values
		v   = df.loc[:,v_col_name].values
		w   = df.loc[:,w_col_name].values

		# extract freestream velocity data if it is there
		has_vel_fs = False

		if ufs_col_name in df and vfs_col_name in df and wfs_col_name in df:
			has_vel_fs = True
			ufs = df.loc[:,ufs_col_name].values
			vfs = df.loc[:,vfs_col_name].values
			wfs = df.loc[:,wfs_col_name].values

		# compute grid dimensions
		xmin = x.min()
		xmax = x.max()
		ymin = y.min()
		ymax = y.max()
		zmin = z.min()
		zmax = z.max() 
		
		nx   = len(np.unique(x))
		ny   = len(np.unique(y))    # number of grid points
		nz   = len(np.unique(z))
		
		dx   = (xmax-xmin)/nx
		dy   = (ymax-ymin)/ny       # grid spacing
		dz   = (zmax-zmin)/nz
		
		xlim = [xmin, xmax]
		ylim = [ymin, ymax]         # grid extents
		zlim = [zmin, zmax]
		
		# reshape to 3-D structured numpy arrays
		# (note that in Python, the final index is the fastest changing)
		X = np.float32(np.reshape(x, [nz, ny, nx]))
		Y = np.float32(np.reshape(y, [nz, ny, nx]))
		Z = np.float32(np.reshape(z, [nz, ny, nx]))

		U = np.float32(np.reshape(u, [nz, ny, nx]))
		V = np.float32(np.reshape(v, [nz, ny, nx]))
		W = np.float32(np.reshape(w, [nz, ny, nx]))

		if has_vel_fs:
			Ufs = np.float32(np.reshape(ufs, [nz, ny, nx]))
			Vfs = np.float32(np.reshape(vfs, [nz, ny, nx]))
			Wfs = np.float32(np.reshape(wfs, [nz, ny, nx]))

		# store data and dimensions as dicts
		grid_data = {'X' : X,
					 'Y' : Y,
					 'Z' : Z,
					 'U' : U,
					 'V' : V,
					 'W' : W}

		if has_vel_fs:
			grid_data['Ufs'] = Ufs
			grid_data['Vfs'] = Vfs
			grid_data['Wfs'] = Wfs

		grid_dims = {'nx' : nx,
					 'ny' : ny,
					 'nz' : nz,
					 'dx' : dx,
					 'dy' : dy,
					 'dz' : dz,
					 'xlim' : xlim,
					 'ylim' : ylim,
					 'zlim' : zlim}

		return grid_data, grid_dims


	def write_vtk_series(self, path, name):
		"""Writes the field data to a time series of VTK files

		Data is written as VTK structured data (.vts). Velocity data is a
		vector field.

		Also writes a Paraview collection file (.pvd) which contains the
		normalized times of each timestep.
		
		Parameters
		----------
		path : str
			The path to which to write the VTK files.
		name : str
			The prefix of the VTK filenames.
		"""

		from pyevtk.hl import gridToVTK 		# evtk module - import only if this function is called
		import xml.etree.cElementTree as ET # xml module  -                 "

		# set the collection filename
		collection_fname = name + ".pvd"

		# set up XML tree for PVD collection file
		root = ET.Element("VTKFile")
		root.set("type", "Collection")
		collection = ET.SubElement(root, "Collection")

		# write the VTK files
		for i, time in enumerate(np.sort(self.times)):
			# get the system time (for elapsed time)
			t_start = tmod.time()

			# get the filename containing the data at current time
			fname = self.fdict[time]

			# base name of data file
			vtk_name = name + '_' + str(i)

			# read the CSV data file
			df_inst              = self.get_df_inst(time=time)
			grid_data, grid_dims = self.fielddata_from_df(df_inst)

			# unpack the grid data
			X = grid_data['X']
			Y = grid_data['Y']
			Z = grid_data['Z']
			U = grid_data['U']
			V = grid_data['V']
			W = grid_data['W']

			# save velocity fields as tuples
			velocity = (U, V, W)

			# create dictionary of data
			pointData = {'velocity' : velocity}
			
			# check if the file has freestream velocity data
			if 'Ufs' in grid_data and 'Vfs' in grid_data and 'Wfs' in grid_data:
				# get the freestream velocity data
				Ufs = grid_data['Ufs']
				Vfs = grid_data['Vfs']
				Wfs = grid_data['Wfs']

				# save as tuple
				velocity_fs = (Ufs, Vfs, Wfs)

				# append to pointdata dictionary
				pointData['velocity_fs']  = velocity_fs

			data_filename = gridToVTK(path + '/' + vtk_name, X, Y, Z, pointData=pointData)

			# add elements to XML tree for PVD collection file
			dataset = ET.SubElement(collection, "DataSet")
			dataset.set("timestep", str(time))
			dataset.set("file", os.path.basename(data_filename))

			# print status message
			elapsed_time = tmod.time() - t_start
			print 'Converted: ' + fname + ' -->\n\t\t\t' + data_filename + ' in %2.2f s\n' % (elapsed_time)

		# write the collection file
		tree = ET.ElementTree(root)
		pvd_filename = os.path.abspath(path + '/' + collection_fname)
		tree.write(pvd_filename, xml_declaration=True)
		print 'Wrote ParaView collection file: ' + pvd_filename


	def field_time_average(self, ti_start=-5, ti_end=-1):
		"""Returns the time-averaged field data over a specified timestep range.

		Averaging is done over the time range self.times[ti_start:ti_end].

		Parameters
		----------
		ti_start : Optional[int]
			The timestep index to start averaging (default -5)
		ti_end : Optional[int]
			The timestep index to end averaging (default -1)

		Returns
		--------
		data_dict_mean : dict
			A dictionary of grid coordinates and time-averaged data.
		"""

		# number of timestep
		num_times = len(self.times[ti_start:ti_end])

		# sum fields
		for ti, time in enumerate(self.times[ti_start:ti_end]):
			df_inst = self.get_df_inst(time=time)
			grid_data, grid_dims = self.fielddata_from_df(df_inst)

			if ti == 0:
				# on the first timestep, save the grid data and initialize variables
				X   = grid_data['X']
				Y   = grid_data['Y']
				Z   = grid_data['Z']

				U   = grid_data['U']
				V   = grid_data['V']
				W   = grid_data['W']
				Ufs = grid_data['Ufs']
				Vfs = grid_data['Vfs']
				Wfs = grid_data['Wfs']
			else:
				# on subsequent timesteps, just add the other fields
				U   = U + grid_data['U']
				V   = V + grid_data['V']
				W   = W + grid_data['W']
				Ufs = Ufs + grid_data['Ufs']
				Vfs = Vfs + grid_data['Vfs']
				Wfs = Wfs + grid_data['Wfs']

		# then divide by the number of steps to get the average
		U   = U/num_times
		V   = V/num_times
		W   = W/num_times
		Ufs = Ufs/num_times
		Vfs = Vfs/num_times
		Wfs = Wfs/num_times

		data_dict_mean = {'t' : self.times[ti_start:ti_end],
					 'X' : X,
					 'Y' : Y,
					 'Z' : Z,
					 'U' : U,
					 'V' : V,
					 'W' : W,
					 'Ufs' : Ufs,
					 'Vfs' : Vfs,
					 'Wfs' : Wfs}
					 
		return data_dict_mean

	def pointdata_time_series(self, p_list, ti_start=0, ti_end=-1):
		"""Extracts a time series of data at a single point or points.

		Loops through the time data to extract a time series of data at a
		specified point or points. Uses nearest-point to avoid interpolation. 
		
		Parameters
		----------
		p_list : list
			List of points, where each point is a tuple of length 3.
		ti_start : Optional[int]
			The timestep index to start (default 0).
		ti_end : Optional[int]
			The timestep index to end (default -1)

		Returns
		-------
		data_dict : dict
			Dictionary of the time series velocity data.
		"""
		# get the grid from the first timestep
		df_inst = self.get_df_inst(time=self.times[0])
		grid_data, grid_dims = self.fielddata_from_df(df_inst)
		
		x = np.unique(grid_data['X'])
		y = np.unique(grid_data['Y'])
		z = np.unique(grid_data['Z'])

		kji_nearest = []

		for p in p_list:
			xp, yp, zp = p
		
			# compute indices of the point closest to xp,yp,zp
			xi = np.abs(x-xp).argmin()
			yi = np.abs(y-yp).argmin()
			zi = np.abs(z-zp).argmin()

			kji_nearest.append((zi,yi,xi))

		# preallocate arrays
		num_times = len(self.times[ti_start:ti_end])
		num_points = len(p_list)

		u   = np.zeros([num_points, num_times])
		v   = np.zeros([num_points, num_times])
		w   = np.zeros([num_points, num_times])
		ufs = np.zeros([num_points, num_times])
		vfs = np.zeros([num_points, num_times])
		wfs = np.zeros([num_points, num_times])

		# loop through the files and extract data
		for ti, time in enumerate(self.times[ti_start:ti_end]):
			# get the dataframe for the current time
			df_inst = self.get_df_inst(time=time)

			# extract data from the dataframe
			grid_data, grid_dims = self.fielddata_from_df(df_inst)

			for pi, coords in enumerate(kji_nearest):
				# extract data at point and store in array
				u[pi, ti]   = (grid_data['U'])[coords]
				v[pi, ti]   = (grid_data['V'])[coords]
				w[pi, ti]   = (grid_data['W'])[coords]
				ufs[pi, ti] = (grid_data['Ufs'])[coords]
				vfs[pi, ti] = (grid_data['Vfs'])[coords]
				wfs[pi, ti] = (grid_data['Wfs'])[coords]

		data_dict = {'t' : self.times[ti_start:ti_end],
					 'u' : u,
					 'v' : v,
					 'w' : w,
					 'ufs' : ufs,
					 'vfs' : vfs,
					 'wfs' : wfs}

		return data_dict


#####################################
######### Module  Functions #########
#####################################
def load_data(data_filename):
	""" load_data(data_filename) : Reads a CSV file using pandas and returns a pandas dataframe """
	
	reader = pd.read_csv(data_filename, iterator=True, chunksize=1000)
	df = pd.concat(reader, ignore_index=True)
	
	df.rename(columns=lambda x: x.strip(), inplace=True)	# strip whitespace from colnames
	return df


def get_file_time(data_filename, time_col_name):
	""" get_file_time(data_filename) : Returns the time of an instantaneous data set by reading the 
		first two rows."""

	with open(data_filename) as f:
		header = f.readline()
		row1   = f.readline()

		time_col_num = header.split(',').index(time_col_name)
		time = float(row1.split(',')[time_col_num])
	
	return time