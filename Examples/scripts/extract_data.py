import os
import copy
import re
import numpy as np
import pandas as pd

UNCERTAINTY_PREFIXES = {
    '_uncrel_': 'relative',
    '_uncabs_': 'absolute',
}

ATOMIC_WEIGHTS = {
    'H': 1.00794,
    'C': 12.0107,
    'N': 14.0067,
    'O': 15.9994,
    'S': 32.065,
    'AR': 39.948,
    'HE': 4.002602,
}

SPECIES_STOICHIOMETRY = {
    'AR': {'AR': 1},
    'HE': {'HE': 1},
    'N2': {'N': 2},
    'O2': {'O': 2},
    'H2': {'H': 2},
    'CO': {'C': 1, 'O': 1},
    'CO2': {'C': 1, 'O': 2},
    'H2O': {'H': 2, 'O': 1},
    'CH4': {'C': 1, 'H': 4},
    'C2H2': {'C': 2, 'H': 2},
    'C2H4': {'C': 2, 'H': 4},
    'C2H6': {'C': 2, 'H': 6},
    'CH3COCH3': {'C': 3, 'H': 6, 'O': 1},
    'C3H6': {'C': 3, 'H': 6},
    'C3H4-A': {'C': 3, 'H': 4},
    'C3H4-P': {'C': 3, 'H': 4},
    'C4H6': {'C': 4, 'H': 6},
    'C4H8-1': {'C': 4, 'H': 8},
    'C5H6': {'C': 5, 'H': 6},
    'CYC5H8': {'C':5, 'H': 8},
    'C6H6': {'C': 6, 'H': 6},
    'C7H8': {'C': 7, 'H': 8},
    'C6H5CH3': {'C': 7, 'H': 8},
    'C6H5OH': {'C': 6, 'H': 6, 'O':1},
    'C6H5OCH3': {'C': 7, 'H': 8, 'O': 1},
    'C6H5C2H5': {'C': 8, 'H': 10},
    'M-XYLENE': {'C': 8, 'H': 10},
    'P-XYLENE': {'C': 8, 'H': 10},
    'NC7H16': {'C': 7, 'H': 16},
    'IC8H18': {'C': 8, 'H': 18},
}

def _clean_column_name(name):
    return re.sub(r'\.\d+$', '', str(name))

def _uncertainty_info(name):
    clean_name = _clean_column_name(name)
    for prefix, kind in UNCERTAINTY_PREFIXES.items():
        if clean_name.startswith(prefix):
            return kind, clean_name[len(prefix):]
    return None, None

def _is_uncertainty_column(name):
    kind, target = _uncertainty_info(name)
    return kind is not None and target != ''

def _active_line(line):
    return line.split('//')[0].strip()

def _os_keyword_values(line, keyword):
    active_line = _active_line(line)
    if keyword not in active_line:
        return None
    return active_line.split(keyword, 1)[1].split(';', 1)[0].strip().split()

def _parametric_commonprop_name(parametric_type):
    return 'parametric {}'.format(parametric_type)

def _store_parametric_analysis(extrainfo, parametric_info):
    parametric_type = parametric_info.get('type')
    if parametric_type is None:
        return
    commonprop_name = _parametric_commonprop_name(parametric_type)
    if 'list_values' in parametric_info:
        values, unit = parametric_info['list_values']
        extrainfo['commonprop'][commonprop_name] = [str(min(values)), str(max(values)), unit]
    elif 'minimum' in parametric_info and 'maximum' in parametric_info:
        min_value, min_unit = parametric_info['minimum']
        max_value, max_unit = parametric_info['maximum']
        if min_unit != max_unit:
            raise ValueError('parametric {} units mismatch: {} {}'.format(parametric_type, min_unit, max_unit))
        extrainfo['commonprop'][commonprop_name] = [min_value, max_value, min_unit]

def _species_stoichiometry(species):
    species_key = str(species).upper()
    stoichiometry = {key.upper(): value for key, value in SPECIES_STOICHIOMETRY.items()}
    if species_key not in stoichiometry:
        raise ValueError('missing stoichiometry for species {}'.format(species))
    return stoichiometry[species_key]

def molecular_weight(species):
    stoichiometry = _species_stoichiometry(species)
    return sum(ATOMIC_WEIGHTS[element.upper()] * count for element, count in stoichiometry.items())

def mole_to_mass_fractions(molefractions):
    species, molefracs = molefractions
    molefracs = np.array(molefracs, dtype=float)
    molecular_weights = np.array([molecular_weight(specie) for specie in species])
    masses = molefracs * molecular_weights
    return dict(zip(species, masses / np.sum(masses)))

def oxygen_moles_for_complete_combustion(species):
    stoichiometry = _species_stoichiometry(species)
    carbon = stoichiometry.get('C', 0)
    hydrogen = stoichiometry.get('H', 0)
    oxygen = stoichiometry.get('O', 0)
    sulfur = stoichiometry.get('S', 0)
    return max(carbon + hydrogen / 4 + sulfur - oxygen / 2, 0)

def fuel_species_from_molefractions(molefractions):
    species = molefractions[0]
    return [specie for specie in species if oxygen_moles_for_complete_combustion(specie) > 0]

def stoich_oxygen_fuel_mass_ratio(fuel_molefractions, fuel_species=None):
    fuel_mass_fractions = mole_to_mass_fractions(fuel_molefractions)
    if fuel_species is None:
        fuel_species = fuel_species_from_molefractions(fuel_molefractions)
    fuel_mass_fraction_sum = sum(fuel_mass_fractions[specie] for specie in fuel_species)
    oxygen_mass_required = 0
    for specie in fuel_species:
        oxygen_mass_required += (
            fuel_mass_fractions[specie]
            / molecular_weight(specie)
            * oxygen_moles_for_complete_combustion(specie)
            * molecular_weight('O2')
        )
    return oxygen_mass_required / fuel_mass_fraction_sum

def stoichiometric_mixture_fraction(fuel_molefractions, oxidizer_molefractions, fuel_species=None, oxidizer_species='O2'):
    fuel_mass_fractions = mole_to_mass_fractions(fuel_molefractions)
    oxidizer_mass_fractions = mole_to_mass_fractions(oxidizer_molefractions)
    if fuel_species is None:
        fuel_species = fuel_species_from_molefractions(fuel_molefractions)
    fuel_mass_fraction_sum = sum(fuel_mass_fractions[specie] for specie in fuel_species)
    oxidizer_mass_fraction = oxidizer_mass_fractions[oxidizer_species]
    mass_stoich_ratio = stoich_oxygen_fuel_mass_ratio(fuel_molefractions, fuel_species=fuel_species)
    return 1 / (1 + mass_stoich_ratio * fuel_mass_fraction_sum / oxidizer_mass_fraction)

def equivalence_ratio(molefractions, fuel_species=None, oxidizer_species='O2'):
    species, molefracs = molefractions
    molefracs = dict(zip(species, np.array(molefracs, dtype=float)))
    if oxidizer_species not in molefracs:
        print('warning: oxidizer species {} not found in molefractions; setting equivalence ratio to 100'.format(oxidizer_species))
        return 100.
    if fuel_species is None:
        fuel_species = fuel_species_from_molefractions(molefractions)
    oxygen_required = sum(
        molefracs[specie] * oxygen_moles_for_complete_combustion(specie)
        for specie in fuel_species
    )
    return oxygen_required / molefracs[oxidizer_species]

def temperature_bounds_from_commonprop(commonprop, names):
    temperatures = []
    for name in names:
        if name in commonprop:
            if len(commonprop[name]) == 0:
                continue
            value, unit = commonprop[name]
            if unit != 'K':
                raise ValueError('temperature {} has unsupported units {}'.format(name, unit))
            temperatures.append(float(value))
    if len(temperatures) == 0:
        raise ValueError('no temperatures found for {}'.format(names))
    return min(temperatures), max(temperatures)

def temperature_bounds(
    extrainfo,
    x=None,
    df_data=None,
    stream_temperature_names=None,
    default=None,
):
    character = extrainfo.get('character', {})
    commonprop = extrainfo.get('commonprop', {})
    stream_temperature_names = (
        ['fuel temperature', 'oxidizer temperature', 'peak mixture temperature', 'temperature']
        if stream_temperature_names is None else stream_temperature_names
    )

    temperature_profile = character.get('T profile', [])
    if len(temperature_profile) > 0:
        profile_temperature_values = [
            value for value in temperature_profile[1::2]
            if str(value).strip() != ''
        ]
        profile_temperatures = np.array(profile_temperature_values, dtype=float)
        if len(profile_temperatures) > 0:
            return float(min(profile_temperatures)), float(max(profile_temperatures))

    parametric_temperature = commonprop.get('parametric temperature', [])
    if len(parametric_temperature) >= 3 and all(str(value).strip() != '' for value in parametric_temperature[:3]):
        return float(parametric_temperature[0]), float(parametric_temperature[1])

    if x is not None and len(x) > 0 and x[0] == 'temperature' and df_data is not None:
        temperatures = []
        for df in df_data.values():
            temperatures += list(df.index)
        if len(temperatures) > 0:
            return float(min(temperatures)), float(max(temperatures))

    available_stream_temperature_names = [
        name for name in stream_temperature_names
        if name in commonprop and len(commonprop[name]) > 0
    ]
    if len(available_stream_temperature_names) > 0:
        return temperature_bounds_from_commonprop(commonprop, available_stream_temperature_names)

    if default is not None:
        return default

    raise ValueError('could not determine temperature bounds from extrainfo or data')

def _find_uncertainty_column(columns, col_idx, col_name, axis, avoid_targets=None):
    target_name = _clean_column_name(col_name)
    avoid_targets = set() if avoid_targets is None else set(avoid_targets)
    candidates = []
    for offset in [1, 2]:
        unc_idx = col_idx + offset
        if unc_idx >= len(columns):
            continue
        kind, target = _uncertainty_info(columns[unc_idx])
        if kind is not None:
            candidates.append((unc_idx, kind, target))

    for unc_idx, kind, target in candidates:
        if target == target_name:
            return unc_idx, kind

    if axis == 'y':
        for unc_idx, kind, target in candidates:
            if target not in avoid_targets:
                return unc_idx, kind

    return None, None

def readdata(filename : str, delzero = True):
    filedf = pd.read_table(filename, sep=r'\s+')
    #print(filedf)
    names = list(filedf.columns)
    #filematrix = np.genfromtxt(filename, skip_header=1, filling_values = 0)
    #filematrix = filematrix.T
    #with open(filename,'r') as f:
    #    names = f.readline().split()
    # create dictionary with different data groups
    # {dg1: Dataframe(index=T, specie:[,,,] ...)
    # delete 0 or NaN values in keys --> generate a dataframe and use remove!
    # remove values with same temperature
    # then concatenate
    #print(filematrix, names)
    datagroups_dct = {}
    datagroups_x_dct = {} #dictionary of only x axis, ordered
    datagroups_uncertainties_dct = {}
    dg_N = 0
    data_col_indices = [i for i, name in enumerate(names) if not _is_uncertainty_column(name)]
    if len(data_col_indices) % 2 != 0:
        raise ValueError('data columns must be x/y pairs after removing uncertainty columns')

    for pair_i in np.arange(0, len(data_col_indices), 2, dtype=int):
        x_i = data_col_indices[pair_i]
        y_i = data_col_indices[pair_i + 1]
        x_name = names[x_i]
        y_name = _clean_column_name(names[y_i])
        if _clean_column_name(y_name) == _clean_column_name(x_name):
            raise ValueError('expected y column after {}, found another x column: {}'.format(x_name, names[y_i]))
        x_unc_i, x_unc_kind = _find_uncertainty_column(names, x_i, x_name, axis='x')
        y_unc_i, y_unc_kind = _find_uncertainty_column(
            names, y_i, y_name, axis='y', avoid_targets=[_clean_column_name(x_name)])
        # dataset = pd.DataFrame(filematrix[i+1], index=filematrix[i], columns=[names[i+1]])
        data = {
            y_name: filedf.iloc[:, y_i].values,
        }
        if x_unc_i is not None:
            data['_uncertainty_x'] = filedf.iloc[:, x_unc_i].values
        if y_unc_i is not None:
            data['_uncertainty_y'] = filedf.iloc[:, y_unc_i].values
        dataset = pd.DataFrame(data, index=filedf.iloc[:, x_i].values)
        dataset = dataset[dataset.index.notna() & dataset[y_name].notna()]
        if delzero == True:
            dataset = dataset[dataset[y_name] > 0]
        dataset = dataset[dataset.index > 0]
        if len(dataset.values) == 0:
            continue # go to next cycle
        # average duplicate x values
        for xi in list(dataset.index):
            if len(dataset.loc[xi].shape) > 1: # duplicate values present
                # average
                avg_series = dataset.loc[xi].mean()
                avg_df = pd.DataFrame([avg_series.values], index = [xi], columns = avg_series.index)
                # delete row
                dataset = dataset.drop(xi)
                # dataset = dataset[~dataset.index.duplicated(keep=False)]
                # concatenate new value with original
                dataset = pd.concat([dataset, avg_df])
                
        x = list(dataset.index)
        x.sort()
        y_dataset = dataset[[y_name]]
        uncertainty_info = {
            'x': None,
            'y': {},
        }
        if x_unc_i is not None:
            uncertainty_info['x'] = {
                'kind': x_unc_kind,
                'values': dataset['_uncertainty_x'],
            }
        if y_unc_i is not None:
            uncertainty_info['y'][y_name] = {
                'kind': y_unc_kind,
                'values': dataset['_uncertainty_y'],
            }
        # print(x, dataset)
        try:
            dg = [key for key, val in datagroups_x_dct.items() if x == val][0]
            # concatenate dataframes
            datagroups_dct[dg] = pd.concat([datagroups_dct[dg], y_dataset], axis = 1)
            if datagroups_uncertainties_dct[dg]['x'] is None and uncertainty_info['x'] is not None:
                datagroups_uncertainties_dct[dg]['x'] = uncertainty_info['x']
            datagroups_uncertainties_dct[dg]['y'].update(uncertainty_info['y'])
        except IndexError:
            dg_N += 1
            dg = 'dg' + str(dg_N)
            datagroups_x_dct[dg] = x
            datagroups_dct[dg] = y_dataset
            datagroups_uncertainties_dct[dg] = uncertainty_info

    for dg, dataset in datagroups_dct.items():
        invalid_columns = [col for col in dataset.columns if _clean_column_name(col).lower() == 'x' or _is_uncertainty_column(col)]
        if len(invalid_columns) > 0:
            raise ValueError('invalid data columns parsed as species in {}: {}'.format(dg, invalid_columns))
        dataset.attrs['uncertainties'] = datagroups_uncertainties_dct[dg]

    #print(datagroups_dct)
    return datagroups_dct


UNITS = {'temperature': ['K'],
         'length': ['m', 'dm', 'cm', 'mm'],
         'time': ['s', 'us', 'ms', 'ns', 'min'],
         'volume': ['m3', 'dm3', 'cm3', 'mm3', 'L'],
         'pressure': ['atm', 'torr', 'Torr', 'kPa', 'MPa', 'Pa', 'bar', 'mbar'],
         }

def readprofile(filename : str):
    data = {}
    # leggi
    profile_data = pd.read_csv(filename, sep = ';', header = None)
    # prime 2 righe: temperature, pressure con relative unità per initial conditions
    # name1: first initial condition; name2: second initial condition
    dct_keys = ['name', 'value', 'units']
    data['init-cond1'] = dict(zip(dct_keys, [profile_data[0][0]] + profile_data.iloc[0][1].split()))
    data['init-cond2'] = dict(zip(dct_keys, [profile_data[0][1]] + profile_data.iloc[1][1].split()))
    # convert to float
    data['init-cond1']['value'] = float(data['init-cond1']['value'])
    data['init-cond2']['value'] = float(data['init-cond2']['value'])
    # 3a riga: qualcosa tra length e time, con relativa unità
    data['x'] = dict(zip(dct_keys, 
                         [profile_data[0][2]] + 
                         [np.array(profile_data[0][5:].values, dtype=float)] + 
                         [profile_data[1][2].strip()]))
    # 4a riga: qualcosa tra temperature, pressure, volume
    data['y'] = dict(zip(dct_keys, 
                         [profile_data[0][3]] + 
                         [np.array(profile_data[1][5:].values, dtype=float)] + 
                         [profile_data[1][3].strip()]))
    
    # checks: initial conditions - names
    init_cond_list = ['temperature', 'pressure', 'time', 'length']
    if data['init-cond1']['name'] not in init_cond_list or data['init-cond2']['name'] not in init_cond_list:
        raise ValueError('initial conditions should be among {}'.format(' '.join(init_cond_list)))
    # checks: x and y values
    if data['x']['name'] not in ['length', 'time']:
        raise ValueError('x should be length or time')
    if data['y']['name'] not in ['temperature', 'volume', 'pressure']:
        raise ValueError('x should be temperature, volume or pressure')        
    # checks: units
    for key in data.keys():
        if data[key]['units'] not in UNITS[data[key]['name']]:
            print(data[key])
            raise ValueError('units for {} should be among {}'.format(data[key]['name'], UNITS[data[key]['name']]))
        
    return data


def nominal_profile_values_from_profiles(
    csv_paths,
    init_condition='init-cond1',
    expected_name='temperature',
):
    nominal_values = []
    for csv_path in csv_paths:
        profile_info = readprofile(csv_path)
        if profile_info[init_condition]['name'] != expected_name:
            raise ValueError(
                '{} should be {}, found {} in {}'.format(
                    init_condition,
                    expected_name,
                    profile_info[init_condition]['name'],
                    csv_path,
                )
            )
        nominal_values.append(profile_info[init_condition]['value'])
    return np.array(nominal_values, dtype=float)


def align_data_to_profile_nominal_values(
    df_data,
    csv_paths,
    init_condition='init-cond1',
    expected_name='temperature',
    dg_id='dg1',
    fillna=0.0,
):
    nominal_values = nominal_profile_values_from_profiles(
        csv_paths,
        init_condition=init_condition,
        expected_name=expected_name,
    )
    print('nominal profile {} values found: {}'.format(expected_name, list(nominal_values)))

    all_species = []
    for df in df_data.values():
        for species in df.columns:
            if species not in all_species:
                all_species.append(species)

    aligned_df = pd.DataFrame(index=nominal_values, columns=all_species, dtype=np.float64)
    for df in df_data.values():
        for species in df.columns:
            scanned_nominal_values = []
            for idx in df.index:
                closest_index = np.abs(nominal_values - idx).argmin()
                closest_nominal_value = nominal_values[closest_index]
                print('assigning {} {} to nominal profile value {}'.format(idx, expected_name, closest_nominal_value))
                if closest_nominal_value in scanned_nominal_values:
                    aligned_df.loc[closest_nominal_value, species] = np.average(
                        [aligned_df.loc[closest_nominal_value, species], df.loc[idx, species]]
                    )
                else:
                    aligned_df.loc[closest_nominal_value, species] = df.loc[idx, species]
                    scanned_nominal_values.append(closest_nominal_value)

    if fillna is not None:
        aligned_df = aligned_df.fillna(fillna)

    return {dg_id: aligned_df}

OS_PROPERTIES = {
    'InletVelocity' : 'velocity',
    '@Pressure' : 'pressure',
    'Length' : 'length',
    'FuelVelocity' : 'fuel velocity',
    'OxidizerVelocity' : 'oxidizer velocity',
    '@ResidenceTime' : 'residence time',
}
MOLEFRACTION_STREAM_KEYS = {
    '@InletStream': 'molefractions',
    '@InitialStatus': 'molefractions',
    '@InletStatus': 'molefractions',
    '@FuelStream': 'molefractions',
    '@OxidizerStream': 'oxidizermolefractions',
}
DICT_NAMES = {
    'InletStream' : [['stringaintrovabile', False], ['Temperature', 'temperature'], 'commonprop'],
    'InletStatus' : [['stringaintrovabile', False], ['Temperature', 'temperature'], 'commonprop'],
    'InitialStatus' : [['stringaintrovabile', False], ['Temperature', 'temperature'], 'commonprop'],
    'FuelStream' : [['stringaintrovabile', False], ['Temperature', 'fuel temperature'], 'commonprop'],
    'OxidizerStream' : [['stringaintrovabile', False],['Temperature', 'oxidizer temperature'], 'commonprop'],
    'PeakMixture' : [['stringaintrovabile', False],['Temperature', 'peak mixture temperature'], 'commonprop'],
    'FixedTemperatureProfile' : [['stringaintrovabile', False],['Profile', 'T profile'], 'character'],
}

def process_osinput(path, osinputname, profiles = False, flameinfo = False):
    """ process OS input file to extract info
    """
    inletstatus = 'stringaintrovabile'
    searchformolefractions = True
    molefraction_key = 'molefractions'
    molefraction_streams = {}
    parametric_dictionary = None
    in_parametric_dictionary = False
    parametric_info = {}
    extrainfo = dict(zip(['profileinfo', 'commonprop', 'character', 'molefractions', 'oxidizermolefractions'],[{},{},{},[],[]]))
    DICT_NAMES_new = copy.deepcopy(DICT_NAMES)
    
    with open(os.path.join(path, osinputname)) as f:
        for line in f:
            active_line = _active_line(line)
            if in_parametric_dictionary and active_line.startswith('}'):
                _store_parametric_analysis(extrainfo, parametric_info)
                in_parametric_dictionary = False
                parametric_info = {}

            if profiles == True and 'ListOfProfiles' in line and '//' not in line.split('ListOfProfiles')[0]:
                print('reminder if sth looks weird - ListOfProfiles must be all in the same row')
                extrainfo['profileinfo']['csv_profiles'] = line.split('ListOfProfiles')[1].split(';')[0].strip().split()
                extrainfo['profileinfo']['csv_paths'] = [os.path.join(path, file) for file in extrainfo['profileinfo']['csv_profiles']]
            
            parametric_analysis_values = _os_keyword_values(line, '@ParametricAnalysis')
            if parametric_analysis_values is not None and len(parametric_analysis_values) > 0:
                parametric_dictionary = parametric_analysis_values[0]

            if parametric_dictionary is not None and active_line.startswith('Dictionary '):
                dictionary_name = active_line.split('Dictionary', 1)[1].split('{', 1)[0].strip()
                if dictionary_name == parametric_dictionary:
                    in_parametric_dictionary = True
                    parametric_info = {}

            if in_parametric_dictionary:
                parametric_type_values = _os_keyword_values(line, '@Type')
                if parametric_type_values is not None and len(parametric_type_values) > 0:
                    parametric_info['type'] = parametric_type_values[0]
                minimum_values = _os_keyword_values(line, '@MinimumValue')
                if minimum_values is not None and len(minimum_values) >= 2:
                    parametric_info['minimum'] = [minimum_values[0], minimum_values[1]]
                maximum_values = _os_keyword_values(line, '@MaximumValue')
                if maximum_values is not None and len(maximum_values) >= 2:
                    parametric_info['maximum'] = [maximum_values[0], maximum_values[1]]
                list_values = _os_keyword_values(line, '@ListOfValues')
                if list_values is not None and len(list_values) >= 2:
                    parametric_info['list_values'] = [
                        np.array(list_values[:-1], dtype=float),
                        list_values[-1],
                    ]

            if flameinfo == True:
                for keyprop, prop_tosciexp in OS_PROPERTIES.items():
                    if keyprop in line and '//' not in line.split(keyprop)[0]:
                        infoitem = line.split(keyprop)[1].split(';')[0].strip().split()
                        if infoitem[0] not in ['true', 'false']:
                            extrainfo['commonprop'][prop_tosciexp] = infoitem # string includes both value and units
                            
            ################# inlet status
            for key in MOLEFRACTION_STREAM_KEYS:
                if key in line and '//' not in line.split(key)[0]:
                    inletstatus = line.split(key)[1].split(';')[0].strip()
                    molefraction_streams[inletstatus] = MOLEFRACTION_STREAM_KEYS[key]
            for streamname, stream_molefraction_key in molefraction_streams.items():
                if streamname in line:
                    inletstatus = streamname
                    molefraction_key = stream_molefraction_key
                    searchformolefractions = True
                    break
            if '@Moles' in line and searchformolefractions == True:
                fuels_and_fracs = line.split(
                    '@Moles')[1].split(';')[0].strip().split()
                extrainfo[molefraction_key] = [
                    fuels_and_fracs[0::2], fuels_and_fracs[1::2]]
                #set to mole fractions
                moles_float = np.array(
                    extrainfo[molefraction_key][1], dtype=float)
                molefracs = moles_float/np.sum(moles_float)
                extrainfo[molefraction_key][1] = [str(frac) for frac in molefracs]
                searchformolefractions = False
            if '@MoleFractions' in line and searchformolefractions == True:
                fuels_and_fracs = line.split('@MoleFractions')[1].split(';')[0].strip().split()
                extrainfo[molefraction_key] = [fuels_and_fracs[0::2], fuels_and_fracs[1::2]]
                searchformolefractions = False
            # find keys for fuelstream and oxidizerstream
            # this way of looking for things is stupid - use automech parser in the future
            for key, val in DICT_NAMES_new.items():    
                if key in line and '//' not in line.split(key)[0]:
                    DICT_NAMES_new[key][0][0] = line.split(key)[1].split(';')[0].strip()     
                    
                if val[0][1] == True and val[1][0] in line and '//' not in line.split(val[1][0])[0]:
                    extrainfo[val[2]][val[1][1]] = line.split(val[1][0])[1].split(';')[0].strip().split()
                    DICT_NAMES_new[key][0][1] = False
                    
                if val[0][0] in line:
                    DICT_NAMES_new[key][0][1] = True
    
            # remove numberofthreads
            if 'NumberOfThreads' in line and '//' not in line.split('@')[0]:
                print('*better avoid NumberOfThreads specification')
            if ('Moles' in line or 'MoleFractions' in line) and ';' not in line:
                print('*Error: input species must be on the same line')

        if in_parametric_dictionary:
            _store_parametric_analysis(extrainfo, parametric_info)
  
    with open(os.path.join(path, osinputname)) as f:
        inputstr = f.read()
        
    return inputstr, extrainfo
