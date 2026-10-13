"""
GUI-only.
Assembles the user-defined parameters from the GUI into a SciExpeM_API.Models.Experiment
object ready for the insertElement(...)
"""

import os
import sys

# Import Tools before anything pulls SciExpeM_API.Models via a `from ... import`.
# Models/__init__ has a circular import (Experiment -> DataColumn -> Tools ->
# `from Models import *`); touching Tools first forces Models to finish building
# so that namespace capture sees every class. GUI.py already does this (SciExpeM.py
# imports Tools first); this keeps experiment_assembler safe on its own too.
import SciExpeM_API.Utility.Tools as _tools  # noqa: F401

from SciExpeM_API.Models import Experiment, FilePaper, CommonProperty, DataColumn

from SciExpeM_API.Utility import extract_data as ed
from SciExpeM_API.Utility import build_sciexp_objects as bso
import os_conditions as osc

# y-name / x-name -> single-letter tag used in the profile dg_label ("T-l history")
LABEL_DCT = {'temperature': 'T', 'time': 't', 'length': 'l', 'pressure': 'p', 'volume': 'V'}

IDT_TYPES = {'ignition delay measurement'}
LFS_TYPES = {'laminar burning velocity measurement'}

# common properties that are always a computed quantity rather than a reported one
_SKIPPED_CP = {'peak mixture temperature'}   # only feeds the T bounds
_CALCULATED_CP = {'velocity', 'strain rate', 'stoichiometric mixture fraction'}


# --------------------------------------------------------------------------- #
# small shared helpers
# --------------------------------------------------------------------------- #
def _clean(value):
    value = '' if value is None else str(value).strip()
    return value or None


def _file_paper(paper):
    year = paper.get('year')
    try:
        year = int(year) if year not in (None, '') else None
    except (TypeError, ValueError):
        year = None
    return FilePaper(
        reference_doi=_clean(paper.get('doi')),
        author=_clean(paper.get('author')),
        title=_clean(paper.get('title')),
        year=year,
        description=_clean(paper.get('description')),
    )


def _expdata_path(files):
    return os.path.join(files.get('folder', ''), files.get('expdata_file', ''))


def _read_df(files, delzero, y_name='y'):
    """Return ``{dg_id: DataFrame}`` from the file, or from the pasted x/y text."""
    if files.get('expdata_mode') == 'paste':
        import pandas as pd

        x = files.get('x_data') or []
        y = files.get('y_data') or []
        if not x or not y:
            raise ValueError('paste mode is selected but no x/y data was entered')
        df = pd.DataFrame({y_name: [float(v) for v in y]}, index=[float(v) for v in x])
        df.attrs['uncertainties'] = {'x': None, 'y': {}}
        return {'dg1': df}

    path = _expdata_path(files)
    if not os.path.isfile(path):
        raise FileNotFoundError('experimental data file not found: {}'.format(path))
    return ed.readdata(path, delzero=delzero)


def _common_properties(extrainfo, x=None, exclude=(), keep_x_temperature=False):
    exclude = set(exclude)
    if x and not (keep_x_temperature and x[0] == 'temperature') and len(x) > 0 and x[0] in ('temperature', 'pressure'):
        exclude.add(x[0])  # it is the swept variable -> captured by t_/p_ bounds

    props = []
    for name, values in extrainfo.get('commonprop', {}).items():
        if name.startswith('parametric ') or name in _SKIPPED_CP:  # synthetic / bounds-only entries
            continue
        if name in exclude:
            continue
        if not values or len(values) < 2 or str(values[0]).strip() == '':
            continue
        source_type = 'calculated' if name in _CALCULATED_CP else 'reported'
        props.append(
            CommonProperty(name=name, units=values[1], value=values[0], source_type=source_type)
        )
    return props


class _AltNameClient(object):
    """
    Utility for searching alternative names
    """

    def __init__(self, client):
        self._client = client

    def __getattr__(self, attr):
        return getattr(self._client, attr)

    def filterDatabase(self, model_name=None, **kwargs):
        found = self._client.filterDatabase(model_name=model_name, **kwargs)
        name = kwargs.get('preferredKey')
        if found or model_name != 'Species' or name is None:
            return found
        found = self._client.filterDatabase(model_name='Species', names__contains=[name])
        if len(found) > 1:
            raise ValueError(
                "Species name '{}' is ambiguous: it is an alternative name of {} species "
                "in the SciExpeM database (ids {}). Use the preferred name in the OS "
                "input file.".format(name, len(found), [sp.id for sp in found]))
        if found:
            print("note: species '{}' found as an alternative name (preferred: {})".format(
                name, getattr(found[0], 'preferredKey', '?')))
        return found


def _parse_formula(formula):
    """
    Chemical formula parser, used for equivalence ratio
    """
    import re
    text = (formula or '').strip().upper()
    if not text:
        return None
    elements = sorted((e.upper() for e in ed.ATOMIC_WEIGHTS), key=len, reverse=True)
    token = re.compile('(' + '|'.join(re.escape(e) for e in elements) + r')(\d*)')
    out, pos = {}, 0
    while pos < len(text):
        m = token.match(text, pos)
        if not m:
            return None
        out[m.group(1)] = out.get(m.group(1), 0) + int(m.group(2) or 1)
        pos = m.end()
    return out


def _ensure_stoichiometry(my_sciexpem, extrainfo):
    """
    Searches the brute formula of any fuel in the SciExpeM db
    so that any name may be used for auto phi evaluation
    E.g. OME2 returns C4H10O3 which is then used by
    the function above to get stoichiometry
    """
    names = list(extrainfo.get('molefractions') or [[]])[0] + \
        list(extrainfo.get('oxidizermolefractions') or [[]])[0]
    atoms = {}
    for name in dict.fromkeys(names):  # unique, ordered
        found = my_sciexpem.filterDatabase(model_name='Species', preferredKey=name)
        if not found:
            raise ValueError(
                "Species '{}' (from the OS input file) was not found in the SciExpeM "
                "database, neither as a preferred nor as an alternative name. Species "
                "must already exist in the DB: fix the name in the OS file, or add the "
                "species to the DB first."
                .format(name))
        try:
            formula = found[0].formula
        except Exception as exc:  # noqa: BLE001 - lazy DB read of the property
            raise ValueError("Species '{}' was found in the SciExpeM database but its "
                             "formula could not be read: {!r}".format(name, exc))
        stoich = _parse_formula(formula)
        if not stoich:
            raise ValueError(
                "Species '{}' is in the SciExpeM database but its formula {!r} cannot "
                "be parsed (known elements: {}). Fix the formula in the DB."
                .format(name, formula, ', '.join(sorted(ed.ATOMIC_WEIGHTS))))
        atoms[name] = stoich
        ed.SPECIES_STOICHIOMETRY[name] = stoich
    extrainfo['atoms'] = atoms


def _element_totals(atoms, composition, elements=('C', 'H', 'O', 'S')):
    """Sum of atoms per element over ``composition`` ({species: amount})."""
    return {e: sum(atoms[sp].get(e, 0) * x for sp, x in composition.items())
            for e in elements}


def equivalence_ratio_element_balance(atoms, composition, cap=100.):
    """
    OpenSMOKEpp definition of the equivalence ratio.
    Currently NOT USED.
    phi = (2 nC + nH/2 + 2 nS) / nO, nX = atoms of X per mole of mixture (oxygen
    in the fuel counts).  Without any O (pyrolysis) the OpenSMOKE value is capped
    at 1e3; here the cap is ``cap`` (100 = the 'pyro' convention of the DB / GUI).
    """
    n = _element_totals(atoms, composition)
    return min((2. * n['C'] + 0.5 * n['H'] + 2. * n['S']) / (n['O'] + 1e-16), cap)


def _mass_fractions(atoms, mole_fractions):
    """{species: mole fraction} -> {species: mass fraction}, MW from the formulas."""
    mw = {sp: sum(ed.ATOMIC_WEIGHTS[el] * n for el, n in atoms[sp].items())
          for sp in mole_fractions}
    mass = {sp: x * mw[sp] for sp, x in mole_fractions.items()}
    total = sum(mass.values())
    return {sp: m / total for sp, m in mass.items()}


def _bilger_beta(atoms, mass_fractions):
    """
    Helper for mixture fraction from OpenSMOKE (CounterFlow flames)
    """
    beta = 0.
    for sp, y in mass_fractions.items():
        mw = sum(ed.ATOMIC_WEIGHTS[el] * n for el, n in atoms[sp].items())
        a = atoms[sp]
        beta += y / mw * (2. * a.get('C', 0) + 0.5 * a.get('H', 0) - a.get('O', 0))
    return beta


def mixture_fraction(atoms, mass, fuel_mass, oxidizer_mass):
    """
    Mixture fraction from OpenSMOKE calculation (CounterFlow flames)
    """
    b, b_f, b_o = (_bilger_beta(atoms, m) for m in (mass, fuel_mass, oxidizer_mass))
    return (b - b_o) / (b_f - b_o)


def stoichiometric_mixture_fraction(atoms, fuel_molefractions, oxidizer_molefractions):
    """
    As name. From OpenSMOKE calculations
    """
    fuel = _mass_fractions(atoms, fuel_molefractions)
    oxidizer = _mass_fractions(atoms, oxidizer_molefractions)
    b_f, b_o = _bilger_beta(atoms, fuel), _bilger_beta(atoms, oxidizer)
    return b_o / (b_o - b_f)


_TO_CM = {'cm': 1.0, 'mm': 0.1, 'm': 100.0}
_V_TO_CMS = {'cm/s': 1.0, 'mm/s': 0.1, 'm/s': 100.0}


def _stream(molefractions):
    species, values = molefractions
    return dict(zip(species, (float(v) for v in values)))


def _counterflow_properties(extrainfo):
    """Calculated common properties of a counterflow flame (from CF notebook)."""
    cp = extrainfo.get('commonprop', {})
    atoms = extrainfo['atoms']
    z_st = stoichiometric_mixture_fraction(
        atoms, _stream(extrainfo['molefractions']), _stream(extrainfo['oxidizermolefractions']))
    props = [CommonProperty(name='stoichiometric mixture fraction', units='unitless',
                            value=float(z_st), source_type='calculated')]
    try:
        (fv, fu), (ov, ou), (ln, lu) = (cp['fuel velocity'][:2], cp['oxidizer velocity'][:2],
                                        cp['length'][:2])
        strain = (abs(float(fv)) * _V_TO_CMS[fu] + abs(float(ov)) * _V_TO_CMS[ou]) / \
            (float(ln) * _TO_CM[lu])
        props.append(CommonProperty(name='strain rate', units='s-1', value=strain,
                                    source_type='calculated'))
    except (KeyError, ValueError) as exc:
        print('warning: strain rate not computed (need @FuelVelocity, '
              '@OxidizerVelocity, @Length in cm|mm|m): {!r}'.format(exc))
    return props


def _counterflow_phi(extrainfo):
    """
    Global equivalence ratio of a counterflow flame.
    """
    cp = extrainfo.get('commonprop', {})
    try:
        flux = {}
        for stream, tname in (('fuel', 'fuel temperature'), ('oxidizer', 'oxidizer temperature')):
            v, u = cp['%s velocity' % stream][:2]
            t, tu = cp[tname][:2]
            if tu != 'K':
                return None
            flux[stream] = abs(float(v)) * _V_TO_CMS[u] / float(t)
        blend = {}
        for stream, key in (('fuel', 'molefractions'), ('oxidizer', 'oxidizermolefractions')):
            for sp, x in _stream(extrainfo[key]).items():
                blend[sp] = blend.get(sp, 0.) + flux[stream] * x
        total = sum(blend.values())
        return ed.equivalence_ratio([list(blend), [str(x / total) for x in blend.values()]])
    except (KeyError, ValueError, ZeroDivisionError) as exc:
        print('note: counterflow phi not computed ({!r}); using 0-100'.format(exc))
        return None


def _profile_csv_paths(extrainfo):
    csv_paths = (extrainfo.get('profileinfo') or {}).get('csv_paths') or []
    if not csv_paths:
        raise RuntimeError(
            'profiles are enabled but the OS input file has no @ListOfProfiles line'
        )
    return csv_paths


def _has_file_uncertainties(df_data):
    for df in df_data.values():
        unc = df.attrs.get('uncertainties') or {}
        if unc.get('x') is not None or unc.get('y'):
            return True
    return False


def _apply_uncertainty_mode(df_data, uncertainty_in_file):
    """
    _uncabs_ vs _uncrel_ 
    """
    if not uncertainty_in_file:
        for df in df_data.values():
            df.attrs['uncertainties'] = {'x': None, 'y': {}}
    return df_data


def _report_dropped_species(df_data, datacols):
    """Print a one-line summary of how many species columns survived DB lookup."""
    wanted = sum(len(df.columns) for df in df_data.values())
    produced = sum(1 for c in datacols if getattr(c, '_name', None) in ('composition', 'concentration'))
    if produced < wanted:
        print('note: {}/{} species columns became data columns; {} dropped '
              '(not found in the SciExpeM Species DB).'.format(
                  produced, wanted, wanted - produced))


# --------------------------------------------------------------------------- #
# bounds resolution: manual entry wins, otherwise infer from the OS file / data
# --------------------------------------------------------------------------- #
def _manual(value):
    value = _clean(value)
    return float(value) if value is not None else None


def _merge_bounds(name, lo, hi, auto_fn):
    """manual entry wins per-field; fall back to ``auto_fn()`` for the rest."""
    if lo is not None and hi is not None:
        return lo, hi
    try:
        auto_lo, auto_hi = auto_fn()
    except Exception as exc:  # noqa: BLE001
        if lo is None and hi is None:
            raise ValueError(
                '{0} bounds could not be inferred from the OS input file / data '
                '({1}); enter {0} INF/SUP by hand in Operating Conditions.'.format(name, exc)
            )
        auto_lo = auto_hi = None
    return (lo if lo is not None else auto_lo, hi if hi is not None else auto_hi)


def _resolve_t_bounds(opcond, extrainfo, x, df_data):
    lo, hi = _manual(opcond.get('T_INF')), _manual(opcond.get('T_SUP'))
    return _merge_bounds('temperature', lo, hi,
                         lambda: osc.temperature_bounds(extrainfo, x=x, df_data=df_data))


def _resolve_p_bounds(opcond, extrainfo, x, df_data):
    unit = opcond.get('P_UNIT') or 'bar'
    lo, hi = _manual(opcond.get('P_INF')), _manual(opcond.get('P_SUP'))
    lo = osc.to_bar(lo, unit) if lo is not None else None
    hi = osc.to_bar(hi, unit) if hi is not None else None
    return _merge_bounds('pressure', lo, hi,
                         lambda: osc.pressure_bounds(extrainfo, x=x, df_data=df_data))


def _resolve_phi_bounds(opcond, extrainfo):
    lo, hi = _manual(opcond.get('PHI_INF')), _manual(opcond.get('PHI_SUP'))
    if lo is not None and hi is not None:
        return lo, hi
    value = None
    try:
        # O2-demand definition (textbook / notebooks); stoichiometry comes from the
        # DB formulas injected by _ensure_stoichiometry
        value = ed.equivalence_ratio(extrainfo['molefractions'])
    except Exception as exc:  # noqa: BLE001 - surfaced to the user, not fatal
        print('warning: could not compute equivalence ratio from the OS mixture:', exc)
    return (lo if lo is not None else value, hi if hi is not None else value)


# --------------------------------------------------------------------------- #
# family: speciation (JSR / flow reactor / flame / concentration-time profile)
# --------------------------------------------------------------------------- #
def _assemble_speciation(paper, files, measure, opcond, my_sciexpem, comment, defaults):
    etype = measure['experiment_type']
    if files.get('expdata_mode') == 'paste':
        raise ValueError(
            'paste mode is only supported for ignition delay / laminar burning '
            'velocity; use a data file (with species headers) for speciation.'
        )
    profiles = bool(files.get('profiles_enabled'))
    unc_in_file = bool(files.get('uncertainty_in_file'))
    x = [measure['x_axis']['variable'], measure['x_axis']['unit']]
    y = [measure['y_axis']['variable'], measure['y_axis']['unit']]
    src_data = files.get('srctype') or 'digitized'
    reactor_mode = measure.get('reactor_mode') or 'premixed'

    inputstr, extrainfo = ed.process_osinput(
        files['folder'], files['OS_input_file'], profiles=profiles, flameinfo=True
    )

    _ensure_stoichiometry(my_sciexpem, extrainfo)

    # profiles need every datagroup on the same x-axis -> keep zeros/NaN rows
    df_data = _apply_uncertainty_mode(_read_df(files, delzero=not profiles), unc_in_file)

    csv_paths = []
    if profiles:
        csv_paths = _profile_csv_paths(extrainfo)
        if defaults.get('align_profiles', True) and x and x[0] == 'temperature':
            if _has_file_uncertainties(df_data):
                print('warning: profile alignment discards the _uncabs_/_uncrel_ '
                      'columns from the data file; the aligned datagroup will carry '
                      'no y-uncertainty.')
            df_data = ed.align_data_to_profile_nominal_values(
                df_data, csv_paths,
                init_condition='init-cond1', expected_name='temperature',
                dg_id='dg1', fillna=0.0,
            )

    inspecies, fuel_objects = bso.build_initial_species(
        my_sciexpem=my_sciexpem,
        molefractions=extrainfo['molefractions'],
        source_type='reported',
        units='mole fraction',
        configuration=reactor_mode,
        oxidizer_molefractions=(extrainfo.get('oxidizermolefractions') or None),
    )

    datacols = bso.build_data_columns(
        df_data=df_data,
        my_sciexpem=my_sciexpem,
        x=x, y=y,
        source_type=src_data,
        label='experimental_data',
        sp_table={},  # alt-name resolution is handled server-side by SciExpeM
        list_exclude_species=[],
        uncert_x=[], uncert_y=[],  # in-file only; no synthetic default
    )
    _report_dropped_species(df_data, datacols)

    if profiles:
        datacols += bso.build_profile_data_columns(
            csv_paths=csv_paths,
            existing_data_groups=list(df_data.keys()),
            label_dct=LABEL_DCT,
            source_type='reported',
        )

    exclude_cp = set()
    if profiles or etype == 'concentration time profile measurement':
        exclude_cp.add('temperature')
    if etype == 'concentration time profile measurement':
        exclude_cp.add('residence time')
    commonprop = _common_properties(extrainfo, x=x, exclude=exclude_cp)
    if etype == 'concentration time profile measurement':
        commonprop = bso.update_residence_time_from_data(commonprop, df_data, x)

    counterflow = reactor_mode == 'counterflow' and bool(extrainfo.get('oxidizermolefractions'))
    if counterflow:
        commonprop += _counterflow_properties(extrainfo)

    t_inf, t_sup = _resolve_t_bounds(opcond, extrainfo, x, df_data)
    p_inf, p_sup = _resolve_p_bounds(opcond, extrainfo, x, df_data)
    if counterflow:  # global phi from the two streams; notebook fallback is 0 - 100
        phi_global = _counterflow_phi(extrainfo)
        phi_inf = _manual(opcond.get('PHI_INF'))
        phi_sup = _manual(opcond.get('PHI_SUP'))
        phi_inf = (0. if phi_global is None else phi_global) if phi_inf is None else phi_inf
        phi_sup = (100. if phi_global is None else phi_global) if phi_sup is None else phi_sup
    else:
        phi_inf, phi_sup = _resolve_phi_bounds(opcond, extrainfo)

    return Experiment(
        reactor=measure['reactor_type'],
        experiment_type=etype,
        file_paper=_file_paper(paper),
        reactor_modes=[reactor_mode],
        data_columns=datacols,
        initial_species=inspecies,
        common_properties=commonprop,
        os_input_file=inputstr,
        t_inf=t_inf, t_sup=t_sup,
        p_inf=p_inf, p_sup=p_sup,
        phi_inf=phi_inf, phi_sup=phi_sup,
        fuels_object=fuel_objects,
        comment=comment,
    )


# --------------------------------------------------------------------------- #
# family: ignition delay (shock tube / RCM)
# --------------------------------------------------------------------------- #
def _simple_xy_datacolumns(df_data, x, y, source_type, label='experimental_data'):
    """One x column + one y column per datagroup, with uncertainty_reference.

    Used for experiment types whose y is not a species (IDT, LFS-vs-x, ...)
    """
    cols = []
    for dg, df in df_data.items():
        x_data = list(df.index)
        y_name = df.columns[0]
        unc = df.attrs.get('uncertainties', {'x': None, 'y': {}})
        x_uref = bso.make_uncertainty_column(
            unc.get('x'), [], x[1], dg, label, x_data, source_type
        )
        y_uref = bso.make_uncertainty_column(
            unc.get('y', {}).get(y_name), [], y[1], dg, label, x_data, source_type
        )
        cols.append(DataColumn(
            name=x[0], units=x[1], dg_id=dg, dg_label=label,
            data=x_data, source_type=source_type, uncertainty_reference=x_uref,
        ))
        cols.append(DataColumn(
            name=y[0], units=y[1], dg_id=dg, dg_label=label,
            data=[float(v) for v in df[y_name]], source_type=source_type,
            uncertainty_reference=y_uref,
        ))
    return cols


def _assemble_idt(paper, files, measure, opcond, my_sciexpem, comment, defaults):
    profiles = bool(files.get('profiles_enabled'))  # RCM volume-time histories
    reactor_type = measure.get('reactor_type') or 'shock tube'
    x = [measure['x_axis']['variable'] or 'temperature', measure['x_axis']['unit'] or 'K']
    y = [measure['y_axis']['variable'] or 'ignition delay', measure['y_axis']['unit'] or 'us']
    src_data = files.get('srctype') or 'reported'

    inputstr, extrainfo = ed.process_osinput(
        files['folder'], files['OS_input_file'], profiles=profiles, flameinfo=True
    )

    _ensure_stoichiometry(my_sciexpem, extrainfo)

    df_data = _apply_uncertainty_mode(
        _read_df(files, delzero=not profiles, y_name='ignition delay'),
        bool(files.get('uncertainty_in_file')),
    )
    datacols = _simple_xy_datacolumns(df_data, x, y, src_data)
    if profiles:
        csv_paths = _profile_csv_paths(extrainfo)
        datacols += bso.build_profile_data_columns(
            csv_paths=csv_paths,
            existing_data_groups=list(df_data.keys()),
            label_dct=LABEL_DCT,
            source_type='reported',
        )

    inspecies, fuel_objects = bso.build_initial_species(
        my_sciexpem=my_sciexpem,
        molefractions=extrainfo['molefractions'],
        source_type='reported',
        units='mole fraction',
        configuration=measure.get('reactor_mode') or 'premixed',
    )

    # shock tube: T is the x axis.  RCM: x is the compressed-gas T, so the OS
    # @Temperature (initial T) is a genuine common property (as in loadexp-RCM).
    rcm = reactor_type == 'rapid compression machine'
    commonprop = _common_properties(
        extrainfo, x=x, exclude=() if rcm else {'temperature'}, keep_x_temperature=rcm)

    t_inf, t_sup = _resolve_t_bounds(opcond, extrainfo, x, df_data)
    p_inf, p_sup = _resolve_p_bounds(opcond, extrainfo, x, df_data)
    phi_inf, phi_sup = _resolve_phi_bounds(opcond, extrainfo)

    reactor_modes = ['reflected shock'] if reactor_type == 'shock tube' else None

    return Experiment(
        reactor=reactor_type,
        experiment_type=measure['experiment_type'],
        ignition_type=measure.get('ignition_type'),
        file_paper=_file_paper(paper),
        reactor_modes=reactor_modes,
        data_columns=datacols,
        initial_species=inspecies,
        common_properties=commonprop,
        os_input_file=inputstr,
        t_inf=t_inf, t_sup=t_sup,
        p_inf=p_inf, p_sup=p_sup,
        phi_inf=phi_inf, phi_sup=phi_sup,
        fuels_object=[s.id for s in fuel_objects],
        comment=comment,
    )


# --------------------------------------------------------------------------- #
# family: laminar burning velocity (equivalence-ratio sweep)
# --------------------------------------------------------------------------- #
def _lfs_reference_mixture(folder, osname, extrainfo):
    """
    Fuel + oxidizer reference mixture of an LFS input as ``[species, fractions]``.
    """
    found = {}
    with open(os.path.join(folder, osname)) as handle:
        for line in handle:
            line = line.split('//')[0]
            for key in ('Fuel', 'Oxidizer'):
                for suffix in ('Moles', 'MoleFractions'):
                    tag = '@' + key + suffix
                    if tag in line:
                        found[key] = line.split(tag)[1].split(';')[0].split()
    if len(found) < 2:
        return extrainfo['molefractions']
    species, values = [], []
    for key in ('Fuel', 'Oxidizer'):
        tokens = found[key]
        total = sum(float(v) for v in tokens[1::2])
        species += tokens[0::2]
        values += [str(float(v) / total) for v in tokens[1::2]]  # each stream sums to 1
    return [species, values]


def _composition_sweep_from_phi(phi_values, extrainfo, oxidizer='O2'):
    """Per-point mole fractions for a phi @ParametricAnalysis.
    """
    species, composition = extrainfo['molefractions']
    reference = dict(zip(species, (float(c) for c in composition)))
    if oxidizer not in reference:
        raise ValueError(
            'the LFS composition sweep needs {} in the OS mixture; got {}'.format(
                oxidizer, species
            )
        )
    fuels = ed.fuel_species_from_molefractions(extrainfo['molefractions'])
    if not fuels:
        raise ValueError('no fuel species identified in the OS mixture for the LFS sweep')
    diluents = [s for s in species if s != oxidizer and s not in fuels]

    fuel_fraction_sum = sum(reference[s] for s in fuels)
    a_stoich = sum(
        reference[s] / fuel_fraction_sum * ed.oxygen_moles_for_complete_combustion(s)
        for s in fuels
    )
    fuel_split = {s: reference[s] / fuel_fraction_sum for s in fuels}
    diluent_per_o2 = {s: reference[s] / reference[oxidizer] for s in diluents}

    out = {s: [] for s in list(fuels) + [oxidizer] + diluents}
    for phi in phi_values:
        moles = {s: phi * fuel_split[s] for s in fuels}
        moles[oxidizer] = a_stoich
        for s in diluents:
            moles[s] = a_stoich * diluent_per_o2[s]
        total = sum(moles.values())
        for s in out:
            out[s].append(moles[s] / total)
    return out


def _assemble_lfs(paper, files, measure, opcond, my_sciexpem, comment, defaults):
    src_data = files.get('srctype') or 'reported'
    y_unit = measure['y_axis']['unit'] or 'cm/s'
    label = 'experimental_data'

    inputstr, extrainfo = ed.process_osinput(
        files['folder'], files['OS_input_file'], profiles=False, flameinfo=True
    )

    extrainfo['molefractions'] = _lfs_reference_mixture(
        files['folder'], files['OS_input_file'], extrainfo)
    _ensure_stoichiometry(my_sciexpem, extrainfo)

    df_data = _apply_uncertainty_mode(
        _read_df(files, delzero=False, y_name='laminar burning velocity'),
        bool(files.get('uncertainty_in_file')),
    )
    if len(df_data) != 1:
        print('warning: LFS expects a single datagroup (phi sweep); got', list(df_data))
    dg, df = next(iter(df_data.items()))
    phi = [float(v) for v in df.index]
    lbv = [float(v) for v in df[df.columns[0]]]
    unc = df.attrs.get('uncertainties', {'x': None, 'y': {}})

    x_uref = bso.make_uncertainty_column(
        unc.get('x'), [], 'unitless', dg, label, phi, src_data
    )
    y_uref = bso.make_uncertainty_column(
        unc.get('y', {}).get(df.columns[0]), [], y_unit, dg, label, phi, src_data,
    )

    datacols = [
        DataColumn(name='equivalence ratio', units='unitless', dg_id=dg, dg_label=label,
                   data=phi, source_type=src_data, uncertainty_reference=x_uref),
        DataColumn(name='laminar burning velocity', units=y_unit, dg_id=dg, dg_label=label,
                   data=lbv, source_type=src_data, uncertainty_reference=y_uref),
    ]

    try:
        sweep = _composition_sweep_from_phi(phi, extrainfo)
        fuel_names = ed.fuel_species_from_molefractions(extrainfo['molefractions'])
    except (ValueError, KeyError) as exc:
        raise ValueError(
            'LFS composition sweep failed ({}). The OS mixture must contain O2, and '
            'every fuel/diluent must be listed in extract_data.SPECIES_STOICHIOMETRY. '
            'Add the missing species there, or switch to a data file that already '
            'carries per-point composition columns.'.format(exc)
        )
    for species_name, fractions in sweep.items():
        species_object = bso.get_species_object(my_sciexpem, species_name)
        datacols.append(DataColumn(
            name='composition', units='mole fraction', dg_id=dg, dg_label=label,
            data=fractions, source_type='calculated', species_object=[species_object],
        ))

    fuel_objects = [bso.get_species_object(my_sciexpem, s) for s in fuel_names]

    commonprop = [c for c in _common_properties(extrainfo)
                  if c.name in ('temperature', 'pressure')]
    t_inf, t_sup = _resolve_t_bounds(opcond, extrainfo, ['equivalence ratio', 'unitless'], df_data)
    p_inf, p_sup = _resolve_p_bounds(opcond, extrainfo, None, None)

    return Experiment(
        reactor='flame',
        experiment_type='laminar burning velocity measurement',
        file_paper=_file_paper(paper),
        reactor_modes=['premixed'],
        data_columns=datacols,
        initial_species=[],  # composition is per-point, carried in the data columns
        common_properties=commonprop,
        os_input_file=inputstr,
        phi_inf=min(phi), phi_sup=max(phi),
        p_inf=p_inf, p_sup=p_sup,
        t_inf=t_inf, t_sup=t_sup,
        fuels_object=[s.id for s in fuel_objects],
        comment=comment,
    )


# --------------------------------------------------------------------------- #
# dispatch
# --------------------------------------------------------------------------- #
def build_experiment(paper, files, measure, opcond, my_sciexpem, comment=None, defaults=None):
    """
    Build (but do not upload) an ``Experiment`` from the four frame dicts.
    """
    defaults = dict(defaults or {})
    my_sciexpem = _AltNameClient(my_sciexpem)
    etype = (measure.get('experiment_type') or '').strip()
    if not etype:
        raise ValueError('select an experiment type in the Measurement Type panel first')

    if etype in IDT_TYPES:
        assemble = _assemble_idt
    elif etype in LFS_TYPES:
        assemble = _assemble_lfs
    else:
        assemble = _assemble_speciation

    return assemble(paper, files, measure, opcond, my_sciexpem, comment, defaults)
