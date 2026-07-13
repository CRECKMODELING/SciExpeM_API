import numpy as np

from SciExpeM_API.Models import CommonProperty, DataColumn, InitialSpecies


DEFAULT_NOTFUELS = ['O2', 'AR', 'HE', 'N2']



def make_uncertainty_column(
    uncertainty_info,
    default_uncertainty,
    units,
    dg,
    label,
    x_data,
    source_type,
):
    if uncertainty_info is not None:
        uncertainty_kind = uncertainty_info['kind']
        uncertainty_data = uncertainty_info['values'].loc[x_data]
        if uncertainty_data.notna().all():
            return DataColumn(
                name='uncertainty',
                units=units,
                dg_id=dg,
                dg_label=label,
                data=list(uncertainty_data),
                source_type=source_type,
                uncertainty_bound='plusminus',
                uncertainty_kind=uncertainty_kind,
            )

    if len(default_uncertainty) > 0:
        uncertainty_kind = default_uncertainty[1]
        return DataColumn(
            name='uncertainty',
            units=units,
            dg_id=dg,
            dg_label=label,
            data=list(default_uncertainty[0] * np.ones(len(x_data))),
            source_type=source_type,
            uncertainty_bound='plusminus',
            uncertainty_kind=uncertainty_kind,
        )

    return None


def find_species_objects(my_sciexpem, y_name, sp_table=None):
    sp_table = {} if sp_table is None else sp_table
    y_name_mapped = sp_table.get(y_name, y_name)
    species_objects = []

    for species_name in y_name_mapped.split('+'):
        species_objects_temp = my_sciexpem.filterDatabase(
            model_name='Species',
            preferredKey=species_name,
        )
        if len(species_objects_temp) == 0:
            print(
                'species {} not as preferred name: alternative names searched'.format(
                    species_name
                )
            )
            species_objects_temp = my_sciexpem.filterDatabase(
                model_name='Species',
                names__contains=[species_name],
            )

        if len(species_objects_temp) == 0:
            print(
                "warning: species {} not found and not inserted in the columns - please check it's what you want".format(
                    y_name
                )
            )
        else:
            species_objects += species_objects_temp

    return species_objects


def get_species_object(my_sciexpem, species_name):
    species_objects = my_sciexpem.filterDatabase(
        model_name='Species',
        preferredKey=species_name,
    )
    if len(species_objects) == 0:
        raise ValueError('species {} not found as preferredKey'.format(species_name))
    return species_objects[0]


def build_initial_species(
    my_sciexpem,
    molefractions,
    source_type='reported',
    units='mole fraction',
    configuration='premixed',
    oxidizer_molefractions=None,
    notfuels=None,
):
    notfuels = DEFAULT_NOTFUELS if notfuels is None else notfuels
    species, composition = molefractions

    if oxidizer_molefractions is None:
        configurations = [configuration] * len(species)
    else:
        oxidizer_species, oxidizer_composition = oxidizer_molefractions
        configurations = ['fuel'] * len(species) + ['oxidizer'] * len(oxidizer_species)
        species = species + oxidizer_species
        composition = composition + oxidizer_composition

    fuels = [specie for specie in species if specie.upper() not in notfuels]
    print('Species:', species)
    print('Fuels:', fuels)
    print('Mole Frac:', composition)
    print('config:', configurations)

    initial_species = []
    fuel_objects = []
    for i, species_name in enumerate(species):
        species_object = get_species_object(my_sciexpem, species_name)
        initial_species.append(
            InitialSpecies(
                name=species_name,
                species=species_object,
                units=units,
                value=composition[i],
                source_type=source_type,
                configuration=configurations[i],
            )
        )

        if species_name in fuels:
            fuel_objects.append(species_object)

    return initial_species, fuel_objects


def _max_x_value(df_data):
    values = []
    for df in df_data.values():
        values += list(df.index)
    return max(values)


def update_residence_time_from_data(commonprop, df_data, x):
    if x[0] != 'time':
        return commonprop

    if x[1] != 's':
        print("warning: time axis units are {}, expected 's' for residence time check".format(x[1]))

    residence_index = None
    residence_property = None
    for i, common_property in enumerate(commonprop):
        if common_property.name == 'residence time':
            residence_index = i
            residence_property = common_property
            break

    if residence_property is None:
        return commonprop

    max_time = _max_x_value(df_data)
    residence_time = float(residence_property.value)
    if max_time < residence_time:
        print(
            'residence time from data ({}) is lower than OS residence time ({}); replacing common property'.format(
                max_time,
                residence_time,
            )
        )
        commonprop[residence_index] = CommonProperty(
            name='residence time',
            units=x[1],
            value=max_time,
            source_type=getattr(residence_property, '_source_type', residence_property.source_type),
        )

    return commonprop


def build_data_columns(
    df_data,
    my_sciexpem,
    x,
    y,
    source_type='digitized',
    label='experimental_data',
    sp_table=None,
    list_exclude_species=None,
    uncert_x=None,
    uncert_y=None,
):
    sp_table = {} if sp_table is None else sp_table
    list_exclude_species = [] if list_exclude_species is None else list_exclude_species
    uncert_x = [] if uncert_x is None else uncert_x
    uncert_y = [] if uncert_y is None else uncert_y
    datacols = []

    for dg, df in df_data.items():
        x_data = list(df.index)
        data_uncertainties = df.attrs.get('uncertainties', {'x': None, 'y': {}})
        x_uref = make_uncertainty_column(
            data_uncertainties.get('x'),
            uncert_x,
            x[1],
            dg,
            label,
            x_data,
            source_type,
        )
        x_datacol = DataColumn(
            name=x[0],
            units=x[1],
            dg_id=dg,
            dg_label=label,
            data=x_data,
            source_type=source_type,
            uncertainty_reference=x_uref,
        )
        datacols.append(x_datacol)

        for y_name in df.columns:
            mapped_species = sp_table.get(y_name, y_name).split('+')
            if y_name in list_exclude_species or any(
                species in list_exclude_species for species in mapped_species
            ):
                continue

            species_objects = find_species_objects(my_sciexpem, y_name, sp_table=sp_table)
            print(y_name, species_objects)

            if len(species_objects) == 0:
                continue

            y_uncertainty = data_uncertainties.get('y', {}).get(y_name)
            y_data = df.loc[x_data][y_name]
            y_uref = make_uncertainty_column(
                y_uncertainty,
                uncert_y,
                y[1],
                dg,
                label,
                x_data,
                source_type,
            )

            y_datacol = DataColumn(
                name=y[0],
                units=y[1],
                dg_id=dg,
                dg_label=label,
                data=list(y_data),
                source_type=source_type,
                species_object=species_objects,
                uncertainty_reference=y_uref,
            )
            datacols.append(y_datacol)

    return datacols


def _datagroup_number(dg_id):
    return int(str(dg_id).split('dg')[1])


def build_profile_data_columns(
    csv_paths,
    existing_data_groups,
    label_dct,
    source_type='reported',
):
    import extract_data

    data_columns = []
    profile_columns = []
    init_cond1 = []
    init_cond2 = []
    data_group_numbers = [_datagroup_number(dg) for dg in existing_data_groups]
    dg0 = max(data_group_numbers)
    if len(data_group_numbers) > 1:
        print(
            'warning - more than 1 datagroup found - there should be just one, where each x corresponds to a different profile output'
        )

    for i, csv_file in enumerate(csv_paths):
        profile_info = extract_data.readprofile(csv_file)
        init_cond1.append(profile_info['init-cond1']['value'])
        init_cond2.append(profile_info['init-cond2']['value'])
        dg_label = (
            label_dct[profile_info['y']['name']]
            + '-'
            + label_dct[profile_info['x']['name']]
            + ' history'
        )

        for key in ['y', 'x']:
            profile_columns.append(
                DataColumn(
                    name=profile_info[key]['name'],
                    units=profile_info[key]['units'],
                    dg_id='dg' + str(dg0 + i + 2),
                    dg_label=dg_label,
                    data=list(profile_info[key]['value']),
                    source_type=source_type,
                    data_group_profile=[str(i + 1)],
                )
            )

    init_conditions = {'init-cond1': init_cond1, 'init-cond2': init_cond2}
    for key in ['init-cond1', 'init-cond2']:
        data_columns.append(
            DataColumn(
                name=profile_info[key]['name'],
                units=profile_info[key]['units'],
                dg_id='dg' + str(dg0 + 1),
                dg_label='initial_condition',
                data=init_conditions[key],
                source_type=source_type,
            )
        )

    return data_columns + profile_columns
