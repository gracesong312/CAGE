import sys, json
import numpy as np
from pygama.dsp.dsp_optimize import *
from pygama import lh5
from energy_selector import select_energies

if len(sys.argv) < 2:
    print("Usage: icpc_optimize_pz [lh5 raw file(s)]")
    sys.exit()

# get input file, dsp_config, and apdb
filenames = sys.argv[1:]
with open('icpc_dsp.json') as f: dsp_config = json.load(f)
with open('icpc_apdb.json') as f: apdb = json.load(f)

# Override dsp_config['outputs'] to contain only what we need for optimization
dsp_config['outputs'] = ['fltp2_sig']

# build a parameter grid for the dsp of choice
pz2_grid = ParGrid()

tau1_values = np.linspace(71, 75, 5)
tau1_values = [ f'{tau:.2f}*us' for tau in tau1_values]
pz2_grid.add_dimension('wf_pz2', 1, tau1_values)

tau2_values = np.linspace(0.5, 5.5, 6)
tau2_values = [ f'{tau:.2f}*us' for tau in tau2_values]
pz2_grid.add_dimension('wf_pz2', 2, tau2_values)

frac_values = np.linspace(0.005, 0.015, 6)
frac_values = [ f'{frac:.3f}' for frac in frac_values]
pz2_grid.add_dimension('wf_pz2', 3, frac_values)

# set up the figure-of-merit to be computed at each grid point
def fltp_sig_mean(tb_out, verbosity):
    mean = np.average(tb_out['fltp2_sig'].nda)
    if verbosity > 1: print(f'mean: {mean}')
    return mean

# set up the energy selection
energy_name = 'energy'
range_name = '208Tl_2615'

# loop over detectors 
detectors = [ 'icpc1', 'icpc2', 'icpc3', 'icpc4' ]
store = lh5.Store()
for detector in detectors:
    # get indices for just a selected energy range
    det_db = apdb[detector]
    lh5_group = 'icpcs/'+detector+'/raw/'
    idx = select_energies(energy_name, range_name, filenames, det_db, lh5_group=lh5_group)

    waveform_name = 'icpcs/' + detector + '/raw/waveform'
    waveforms, _ = store.read_object(waveform_name, filenames, idx=idx)
    print(f'{len(waveforms)} wfs for {detector}')

    # build the table for processing
    tb_data = lh5.Table(col_dict = { 'waveform' : waveforms } )

    # run the optimization
    db_dict = apdb[detector]
    grid_values = run_grid(tb_data, dsp_config, pz2_grid, fltp_sig_mean, db_dict=db_dict, verbosity=0)

    # analyze the results
    i_min = np.argmin(grid_values)
    i_min = np.unravel_index(i_min, grid_values.shape)
    print(f'{detector}: min {grid_values[i_min]:.3f} at {tau1_values[i_min[0]]}, {tau2_values[i_min[1]]}, {frac_values[i_min[2]]}')

