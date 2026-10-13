"""
Helper for the GUI upload
"""

from SciExpeM_API.Utility import extract_data as ed

# atm/torr/... -> bar.  Keeps the spellings that appear both in OpenSMOKE input
# files and in the GUI unit drop-downs.
CONVERT_TO_BAR = {
    'bar': 1.0,
    'mbar': 1.0e-3,
    'atm': 1.01325,
    'Pa': 1.0e-5,
    'kPa': 1.0e-2,
    'MPa': 10.0,
    'Torr': 1.01325 / 760.0,
    'torr': 1.01325 / 760.0,
    'mmHg': 1.01325 / 760.0,
}

# re-export so callers can do ``from os_conditions import temperature_bounds``
temperature_bounds = ed.temperature_bounds


def to_bar(value, unit):
    """Convert ``value`` given in ``unit`` to bar."""
    key = str(unit).strip()
    if key not in CONVERT_TO_BAR:
        raise ValueError(
            'unsupported pressure unit {!r}; known units: {}'.format(
                unit, ', '.join(sorted(CONVERT_TO_BAR))
            )
        )
    return float(value) * CONVERT_TO_BAR[key]


def pressure_bounds(extrainfo, x=None, df_data=None, default=None):
    """Best-effort (p_inf, p_sup) in bar from a processed OS input file.

    Resolution order (mirrors :func:`extract_data.temperature_bounds`):

    1. ``@ParametricAnalysis`` of ``@Type pressure`` -> ``commonprop['parametric pressure']``
    2. the x-axis itself is pressure -> min/max of the experimental data
    3. a single ``@Pressure`` statement -> ``commonprop['pressure']`` (inf == sup)
    4. ``default`` if provided, otherwise ``ValueError``.
    """
    commonprop = extrainfo.get('commonprop', {})

    parametric = commonprop.get('parametric pressure', [])
    if len(parametric) >= 3 and all(str(v).strip() != '' for v in parametric[:3]):
        return to_bar(parametric[0], parametric[2]), to_bar(parametric[1], parametric[2])

    if x is not None and len(x) >= 2 and x[0] == 'pressure' and df_data:
        values = [v for df in df_data.values() for v in df.index]
        if values:
            return to_bar(min(values), x[1]), to_bar(max(values), x[1])

    pressure = commonprop.get('pressure', [])
    if len(pressure) >= 2 and str(pressure[0]).strip() != '':
        bar = to_bar(pressure[0], pressure[1])
        return bar, bar

    if default is not None:
        return default

    raise ValueError('could not determine pressure bounds from the OS input file or the data')
