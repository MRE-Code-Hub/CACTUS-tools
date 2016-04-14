"""Module for handling probe data from a CACTUS simulation."""

import glob
import pandas as pd
import matplotlib.pyplot as plt

from recursive_glob import recursive_glob

class CactusProbes():
    """Probes class for CACTUS probe data.

    Attributes
    ----------
    probe_locations : dict
        Dictionary of {probe_id (int) : prob_location (numpy.array)}
    probe_filenames : dict
        Dictionary of {probe_id (int) : prob_filename (str)}
    """

    def __init__(self):
        """Initializes Probes class."""
        self.probe_locations = {}
        self.probe_filenames = {}


    def read_probe_files(self, run_directory):
        """Find probe files in run directory and read the headers.

        Searches within the specified run directory to find files matching the
        pattern `*probe*.csv`. Reads in the header data to class attributes.

        Parameters
        ----------
        run_directory : str
            Path to the directory containing probe data files.
        """

        # find files in run_directory which match probe*.csv
        probe_filenames = recursive_glob(run_directory, '*probe*.csv')

        # read in the location of each probe (not the data)
        # add the probe location and filenames
        for probe_id,probe_filename in enumerate(sorted(probe_filenames)):
            with open(probe_filename) as f:
                # read the location of the probe
                tmp = f.readline()
                splitline = f.readline().split(',')
                
                if len(splitline) == 3:
                    x,y,z = splitline
                elif len(splitline) == 4:
                    x,y,z,tmp = splitline
                    
                # store probe location and filename to dictionary
                self.probe_locations[probe_id] = (float(x),float(y),float(z))
                self.probe_filenames[probe_id] = probe_filename


    def get_probe_data_by_id(self, probe_id):
        """Returns a Pandas dataframe of the probe data with given id.

        Parameters
        ----------
        probe_id : int
            ID of the probe we wish to get data from.

        Returns
        -------
        df : pandas.DataFrame
            DataFrame of the probe data.
        """

        probe_filename = self.probe_filenames[probe_id]
        return pd.read_csv(probe_filename,skiprows=2)


    def plot_probe_data_by_id(self, probe_id, ax=None, timestep=False, plot_fs=False):
        """Plots the velocity vs. time for a specific probe.

        Parameters
        ----------
        probe_id : int
            Probe ID to plot
        ax : matplotlib axis
            Axis on which to plot series. If not specified, creates a new figure.
        timestep : Optional[bool]
            True to plot x-axis as timestep instead of normalized time (default
            False).
        plot_fs : Optional[bool]
            True to plot freestream velocities in addition to induced velocities
            (default False)

        Returns
        -------
        figure : matplotlib.figure.Figure
            Figure handle.
        ax : matplotlib.axes._subplots.AxesSubplot
            Axis handle.
        """

        df = self.get_probe_data_by_id(probe_id)
        
        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111)

        # plot velocities with either timestep or normalized time for x-axis
        if timestep:
            ax.plot(df['U/Uinf (-)'], label='U/Uinf (-)')
            ax.plot(df['V/Uinf (-)'], label='V/Uinf (-)')
            ax.plot(df['W/Uinf (-)'], label='W/Uinf (-)')
            ax.set_xlabel('Timestep')
        else:
            ax.plot(df['Normalized Time (-)'], df['U/Uinf (-)'], label='U/Uinf (-)')
            ax.plot(df['Normalized Time (-)'], df['V/Uinf (-)'], label='V/Uinf (-)')
            ax.plot(df['Normalized Time (-)'], df['W/Uinf (-)'], label='W/Uinf (-)')
            ax.set_xlabel('Normalized Time (-)')

        # plot the free-stream (if requested)
        if plot_fs:
            ax.plot(df['Ufs/Uinf (-)'], label='Ufs/Uinf (-)')
            ax.plot(df['Vfs/Uinf (-)'], label='Vfs/Uinf (-)')
            ax.plot(df['Wfs/Uinf (-)'], label='Wfs/Uinf (-)')

        ax.set_ylabel('Normalized Velocity (-)')
        ax.set_title(r'Velocity at $p=(%2.2f,%2.2f,%2.2f)$' % (self.probe_locations[probe_id]))
        ax.grid(True)
        ax.legend(loc='best')

        return fig, ax

    @property
    def num_probes(self):
        """The number of probes."""
        return len(self.probe_locations)