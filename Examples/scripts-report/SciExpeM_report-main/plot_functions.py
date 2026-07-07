from copy import deepcopy
import pandas as pd
import sys
import numpy as np
import math
from secrets import choice
from collections import OrderedDict
import copy 

def find_fuels(exp):
    fuels = []
    for j in exp:
        if j.fuels:
            # should be deprecated
            fuels.extend(j.fuels.replace('[','').replace(']','').replace('"','').replace(' ','').split(','))
        elif j.fuels_object:
            # right one, but API doesn't work
            fuels.extend([spob.species_object[0]['preferredKey'] for spob in j.fuels_object])
        elif j.initial_species:
            # workaround, but always works
            fuels.extend([sp.species.preferredKey for sp in j.initial_species if sp.species.preferredKey not in ['AR', 'N2', 'O2', 'HE']])
        elif j.data_columns: #for LFS
            fuels.extend([col.species_object[0]['preferredKey'] for col in j.data_columns if col.species_object if col.species_object[0]['preferredKey'] not in ['AR', 'N2', 'O2', 'HE']])

    fuels = list(sorted(set(fuels)))
    fuels = [element.replace("n-", "N").replace("N-", "N") for element in fuels]
    return fuels 

def get_fuels_targets(AllExecs, fuels, targets, list_data_columns):
    """
    :param AllExecs: list of executions with the selected chem model
    :type AllExecs: list of SciExpeM_API.Models.Execution.Execution
    :param fuels: list of all fuels simulated with the selected model (if empty it is automatically fetched)
    :type fuels: list of str
    :param targets: list of all targets simulated with the selected model (if empty it is automatically fetched)
    :type targets: list of str

    :return: list of executions with chem model, list of IDs of experiments simulated with chem model, list of fuels of the experiments
    :rtype: list of lists
    """

    if len(fuels)==0:
        #this is the iper-slow step since it requires internet connections to the SciExpeM database
        allexps = [execs.experiment for execs in AllExecs]
        fuels = find_fuels(allexps)
        
    if len(targets)==0:
        targets = [i.species_object[0]['preferredKey'] for i in list_data_columns if i.species_object]
        targets = list(set(targets))

    return fuels, targets



def get_listExp(my_sciexpem, AllExecs, fuel, exp_type, target, list_list_data_columns, list_data_columns):
    """
    :return: sublist of IDs of experiments simulated with the selected chem model, for chosen fuel, exp_type and target
    """
    
    listExp = []
    list_ExpIDwithExec = [j.experiment.id for j in AllExecs]
    list_ExpIDwithExecAndTarget = list_ExpIDwithExec

    if exp_type != 'ignition delay measurement' and exp_type != 'laminar burning velocity measurement': 
        list_ExpIDwithExecAndTarget = []
        for i in list_data_columns:
            if i.species_object:
                if i.species_object[0]['preferredKey'] == target:
                    for idj, j in enumerate(list_list_data_columns):
                        if i in j:
                            list_ExpIDwithExecAndTarget.append(list_ExpIDwithExec[idj])
                            break
    #list_ExpIDwithExecAndTarget = list(OrderedDict.fromkeys(list_ExpIDwithExec))
    #print(list_ExpIDwithExecAndTarget)
    # Experiments = my_sciexpem.filterDatabase(model_name='Experiment', status = 'verified', experiment_type = exp_type) # c'era il filtro per fuels. sbagliato.!
    #print(Experiments)
    Experiments = copy.deepcopy(list_ExpIDwithExecAndTarget)
    for ID in Experiments:
        exp = my_sciexpem.filterDatabase(model_name='Experiment', id = ID)[0] # c'era il filtro per fuels. sbagliato.!
        if exp.experiment_type != exp_type:
            list_ExpIDwithExecAndTarget.remove(ID)
            continue
        if exp_type != 'laminar burning velocity measurement': #unico senza initial species
            #print(exp.id)
            if fuel not in [sp.species.preferredKey for sp in exp.initial_species]:
                list_ExpIDwithExecAndTarget.remove(ID)
        else:
            # different filter for column name
            #fuelsexp = []
            #for col in exp.data_columns:
            #    if col.name == 'composition':
            #        fuelsexp.append(col.species_object[0]['preferredKey'])
            #if fuel not in fuelsexp:
            if fuel not in [col.species_object[0]['preferredKey'] for col in exp.data_columns if col.species_object]:
                list_ExpIDwithExecAndTarget.remove(ID)
                
    # listExp = [j.id for j in list_ExpIDwithExecAndTarget]
    # listExp = [j.id for j in Experiments]
    # listExp = [element for element in listExp if element in list_ExpIDwithExecAndTarget]
    listExp = list(OrderedDict.fromkeys(list_ExpIDwithExecAndTarget))

    return listExp



def get_xyexp(my_sciexpem, Exp, exp_type, ID, target):
    """
    :return: x and y axes of the selected ID-experiment
    """

    warn_exp = False
    x_multiplier = 1
    y_multiplier = 1
    y_unc_multiplier = 1
    
    match exp_type:
        case 'ignition delay measurement':
            x_exp_key = 'temperature [K]'
            y_exp_key = 'ignition delay'
            y_exp = Exp[0].experimental_data[0].filter(like=y_exp_key,axis=1)
            #y_exp = Exp[0].experimental_data[0]['ignition delay']
            if '[s]' not in y_exp.columns[0]:
                if '[us]' in y_exp.columns[0]:
                    y_exp = 1e-6 * y_exp
                if '[ms]' in y_exp.columns[0]:
                    y_exp = 1e-3 * y_exp
            x_exp = 1000/Exp[0].experimental_data[0][x_exp_key]
            y_exp = y_exp.iloc[:,0]
            y_exp_unc = Exp[0].experimental_data[0].filter(like='uncertainty',axis=1)
            # bug nell'unità di misura delle incertezze. Qui si è considerato sempre [s]
            y_unc_multiplier = 1e-6

        case 'laminar burning velocity measurement':
            if 'equivalence ratio [unitless]' in Exp[0].experimental_data[0].columns:
                x_exp_key = 'equivalence ratio [unitless]'
            else:
                x_exp_key = 'pressure [bar]'
            y_exp_key = 'laminar burning velocity'
            x_exp = Exp[0].experimental_data[0][x_exp_key]
            y_exp = Exp[0].experimental_data[0].filter(like=y_exp_key,axis=1)
            y_exp = y_exp.iloc[:,0]
            y_exp_unc = Exp[0].experimental_data[0].filter(like='uncertainty',axis=1)

        case 'jet stirred reactor measurement':
            x_exp_key = 'temperature [K]'
            y_exp_key = target+' [mole fraction]'
            y_exp_unc = 0
            warn_exp = True
            check = 0
            for i in Exp[0].experimental_data:
                if y_exp_key in i.columns: 
                    #y_exp = i.filter(like=y_exp_key,axis=1)
                    y_exp = i[y_exp_key]
                    x_exp = i[x_exp_key]
                    y_exp_unc = i.filter(like='uncertainty',axis=1)
                    warn_exp = False
                    check = 1
                    break
            if type(y_exp_unc)==int and check == 1:
                print('\t\tWARNING: bug in sciexpem to be fixed')
                print()
                return 0,0,0,0
            elif type(y_exp_unc)==int and check == 0:
                # target not found
                return 0,0,0,0

        case 'outlet concentration measurement':
            x_exp_key = 'temperature [K]'
            y_exp_key = target+' [mole fraction]'
            y_exp = pd.DataFrame([0,1])
            x_exp = pd.DataFrame([0,1])
            y_exp_unc = pd.DataFrame()
            warn_exp = True

            for i in Exp[0].experimental_data:
                if y_exp_key in i.columns: 
                    #y_exp = i.filter(like=y_exp_key,axis=1)
                    y_exp = i[y_exp_key]
                    x_exp = i[x_exp_key]
                    y_exp_unc = i.filter(like='uncertainty',axis=1)
                    warn_exp = False
                    break

        case 'concentration time profile measurement':
            if 'residence time [s]' in Exp[0].experimental_data[0].columns:
                x_exp_key = 'residence time [s]'
            elif 'time [s]' in Exp[0].experimental_data[0].columns:
                x_exp_key = 'time [s]'
            elif 'time [ms]' in Exp[0].experimental_data[0].columns:
                x_exp_key = 'time [ms]'
            elif 'time [us]' in Exp[0].experimental_data[0].columns:
                x_exp_key = 'time [us]'
            elif 'pressure [bar]' in Exp[0].experimental_data[0].columns:
                x_exp_key = 'pressure [bar]'
            y_exp_key = target + ' [mole fraction]'
            y_exp = pd.DataFrame([0,1])
            x_exp = pd.DataFrame([0,1])
            y_exp_unc = pd.DataFrame()
            warn_exp = True

            for i in Exp[0].experimental_data:
                if y_exp_key in i.columns: 
                    #y_exp = i.filter(like=y_exp_key,axis=1)
                    if x_exp_key == 'pressure [bar]': x_multiplier = 1e5 # Plot always in [Pa] as in OpenSMOKE++
                    if x_exp_key == 'time [ms]': x_multiplier = 1e-3     # Plot always in [s]  as in OpenSMOKE++
                    if x_exp_key == 'time [us]': x_multiplier = 1e-6     # Plot always in [s]  as in OpenSMOKE++
                    y_exp = i[y_exp_key]                
                    x_exp = i[x_exp_key] * x_multiplier 
                    y_exp_unc = i.filter(like='uncertainty',axis=1)
                    warn_exp = False
                    break

        case 'burner stabilized flame speciation measurement':
            if target == 'soot volume fraction':  y_exp_key = target + ' [unitless]'  # special target for soot
            elif target == 'number density':  y_exp_key = target + ' [cm-3]'          # special target for soot
            elif target == 'particle diameter':  y_exp_key = target + ' [nm]'         # special target for soot  
            elif target == 'primary particle diameter':  y_exp_key = target + ' [nm]' # special target for soot
            else: y_exp_key = target + ' [mole fraction]'
            y_exp = pd.DataFrame([0,1])
            
            column_index = ''
            for i in range(len(Exp[0].experimental_data)):              # find the column index of the desired target
                if y_exp_key in Exp[0].experimental_data[i].columns: 
                    column_index = i
            if column_index == '':
                return 0, 0, 0, 0
            try: 
                if 'time [s]' in Exp[0].experimental_data[column_index].columns:
                    x_exp_key = 'time [s]'
                elif 'residence time [ms]' in Exp[0].experimental_data[column_index].columns:
                    x_exp_key = 'residence time [ms]'
                elif 'distance [m]' in Exp[0].experimental_data[column_index].columns:
                    x_exp_key = 'distance [m]'
                elif 'distance [cm]' in Exp[0].experimental_data[column_index].columns:
                    x_exp_key = 'distance [cm]'
                elif 'distance [mm]' in Exp[0].experimental_data[column_index].columns:
                    x_exp_key = 'distance [mm]'
            except: 
                print('WARNING: bug in sciexpem to be fixed for target {} - BSFSM exp'.format(target))
                return 0, 0, 0, 0
            try:
                x_exp_key
            except:
                print('WARNING: bug in sciexpem to be fixed for target {} - BSFSM exp'.format(target))
                return 0, 0, 0, 0

            x_exp = pd.DataFrame([0,1])
            y_exp_unc = pd.DataFrame()
            warn_exp = True

            for i in Exp[0].experimental_data:
                if y_exp_key in i.columns: 
                    #y_exp = i.filter(like=y_exp_key,axis=1)
                    if x_exp_key == 'distance [m]': x_multiplier = 1e2           # Plot always in [cm] as in OpenSMOKE++
                    elif x_exp_key == 'distance [mm]': x_multiplier = 1e-1       # Plot always in [cm] as in OpenSMOKE++
                    elif x_exp_key == 'residence time [ms]': x_multiplier = 1e-3 # Plot always in [s] as in OpenSMOKE++
                    y_exp = i[y_exp_key]                
                    x_exp = i[x_exp_key] * x_multiplier
                    y_exp_unc = i.filter(like='uncertainty',axis=1)
                    warn_exp = False
                    break

    if len(y_exp_unc.columns)>0:
        y_exp_unc = pd.to_numeric(y_exp_unc.iloc[:,0])
        DataColumn = my_sciexpem.filterDatabase(model_name='DataColumn', experiment = ID)
        uncertainty = 'relative'
        #if 'absolute'
        for i in DataColumn:
            if i.uncertainty_kind == 'absolute':
                uncertainty = 'absolute'    
                break
            elif i.uncertainty_kind == 'relative':    
                break             
        if uncertainty == 'absolute':
            y_unc_abs = y_exp_unc * y_unc_multiplier # absolute uncertainty
        else:
            y_unc_abs = y_exp * y_exp_unc # relative uncertainty
    else:
        y_unc_abs = []

    return x_exp, y_exp, y_unc_abs, warn_exp



def get_xysim(Exec,exp_type,target):
    """
    :return: x and y axes of model simulation for the selected ID-experiment
    """
    warn_sim = False

    match exp_type:
        case 'ignition delay measurement':
            bigkey_sim = 'ParametricAnalysisIDT'
            x_key_sim = 'T0'
            y_key_sim = 'tau'
        case 'laminar burning velocity measurement':
            bigkey_sim = 'FlameSpeeds'
            if 'Eq.Ratio' in Exec[0].simulation_results[0]['FlameSpeeds'].columns:
                x_key_sim = 'Eq.Ratio'
            else: 
                x_key_sim = 'Pressure'
            y_key_sim = 'Speed'
        case 'jet stirred reactor measurement':
            bigkey_sim = 'ParametricAnalysis'
            if 'T0' in Exec[0].simulation_results[0][bigkey_sim].columns:
                x_key_sim = 'T0'
            else:
                x_key_sim = 'T'
            y_key_sim = target+'_x'
        case 'outlet concentration measurement':
            bigkey_sim = 'ParametricAnalysis'
            if 'T0' in Exec[0].simulation_results[0][bigkey_sim].columns:
                x_key_sim = 'T0'
            else:
                x_key_sim = 'T'
            y_key_sim = target+'_x'
        case 'concentration time profile measurement':
            if 'ParametricAnalysis' in Exec[0].simulation_results[0]:
                bigkey_sim = 'ParametricAnalysis'
            elif 'Output' in Exec[0].simulation_results[0]:
                bigkey_sim = 'Output'
            if 't' in Exec[0].simulation_results[0][bigkey_sim]:
                x_key_sim = 't'
            elif 'P' in Exec[0].simulation_results[0][bigkey_sim]:
                x_key_sim = 'P'
            y_key_sim = target+'_x'
        case 'burner stabilized flame speciation measurement':
            if 'Solution.final' in Exec[0].simulation_results[0]:
                bigkey_sim = 'Solution.final'
            elif 'Solution.soot' in Exec[0].simulation_results[0]:
                bigkey_sim = 'Solution.soot'
            if 't' in Exec[0].simulation_results[0][bigkey_sim]:
                x_key_sim = 't'
            elif 'x' in Exec[0].simulation_results[0][bigkey_sim]:
                x_key_sim = 'x'
            if bigkey_sim == 'Solution.soot': 
                if target == 'soot volume fraction': y_key_sim = 'fv(tot)'
                elif target == 'number density': y_key_sim = 'N(tot)'
                elif target == 'particle diameter': y_key_sim = 'D63(tot)'
                elif target == 'primary particle diameter': y_key_sim = 'Dpp'
            else: y_key_sim = target+'_x'

    x_sim = Exec[0].simulation_results[0][bigkey_sim][x_key_sim]
    sorted_indices = np.argsort(x_sim)
    x_sim = [x_sim[i] for i in sorted_indices]
    if exp_type == 'ignition delay measurement':
        x_sim = [1000/x for x in x_sim] # plottare 1000/T anzichè T

    if exp_type == 'jet stirred reactor measurement' or exp_type == 'outlet concentration measurement' \
        or exp_type == 'concentration time profile measurement' or exp_type == 'burner stabilized flame speciation measurement':
        if y_key_sim in Exec[0].simulation_results[0][bigkey_sim].columns:
            y_sim = Exec[0].simulation_results[0][bigkey_sim][y_key_sim]
        else:
            y_sim = [0] * len(x_sim)
            warn_sim = True
    else:
        y_sim = Exec[0].simulation_results[0][bigkey_sim].filter(like=y_key_sim,axis=1).iloc[:,0]
    y_sim = [y_sim[i] for i in sorted_indices]

    return x_sim, y_sim, warn_sim



def get_xyrange(Exp,y_sim_max,x_exp,y_exp,extra_x,extra_y,exp_type, target):

    yscale = 'linear'
    x_lenght = x_exp.max()-x_exp.min()
    x_range = [x_exp.min()-x_lenght*extra_x,x_exp.max()+x_lenght*extra_x]
    y_range = []
    tick_positions = []
    y_minn = 0

    match exp_type:
        case 'ignition delay measurement':
            # plot only y-ticklabels for 10 multiples/submultiples, in log10 scale
            y_minn = y_exp.min()
            y_minn = 10 ** math.ceil(math.log10(y_minn)) / 10
            xlabel = '1000/T [1/K]'
            ylabel = 'IDT [s]'
            yscale = 'log'
        case 'laminar burning velocity measurement':
            if 'equivalence ratio [unitless]' in Exp[0].experimental_data[0].columns:
                xlabel = '$\Phi$ [-]'
            else:
                xlabel = 'P [bar]'
            ylabel = 'LFS [cm/s]'
        case 'jet stirred reactor measurement':
            xlabel = 'T [K]'
            ylabel = 'mole fraction [-]'
        case 'outlet concentration measurement':
            xlabel = 'T [K]'
            ylabel = 'mole fraction [-]'
        case 'concentration time profile measurement':
            if 'pressure [bar]' in Exp[0].experimental_data[0].columns:
                xlabel = 'P [Pa]'
            else: xlabel = 't [s]'
            ylabel = 'mole fraction [-]'
        case 'burner stabilized flame speciation measurement':
            xlabel = 'axial coordinate [cm]'
            if target == 'soot volume fraction': ylabel = 'fv [-]'
            elif target == 'number density': ylabel = 'N [cm-3]'
            elif target == 'particle diameter': ylabel = 'D63 [nm]'
            elif target == 'primary particle diameter': ylabel = 'Dpp [nm]'
            else: ylabel = 'mole fraction [-]'
            
    y_maxx = y_exp.max()
    y_maxx = 10 ** math.ceil(math.log10(y_maxx))

    y_range = [y_minn,y_maxx]
    y_range[1] = max(y_range[1],y_sim_max)

    if exp_type != 'ignition delay measurement':
        tick_positions = np.linspace(0,y_range[1], 5)
    else:
        tick_positions = np.logspace(np.log10(y_minn), np.log10(y_maxx), int(np.abs(np.log10(y_maxx)-np.log10(y_minn))+1))
    
    return x_range, y_range, xlabel, ylabel, yscale, tick_positions



def get_expprop(Exp, FilePaper, ID):
    author = 'NONE'
    if Exp[0].file_paper != None and FilePaper[0].author != None:
        author = FilePaper[0].author.split(",")[0]
    Tmin = int(Exp[0].t_inf)
    Tmax = int(Exp[0].t_sup)
    Pmin = Exp[0].p_inf
    Pmax = Exp[0].p_sup
    PHImin = Exp[0].phi_inf
    PHImax = Exp[0].phi_sup
    if Tmin == Tmax:
        T = str(Tmin)
    else:
        T = str(Tmin)+'-'+str(Tmax)
    if Pmin == Pmax:
        P = str(Pmin)
    else:
        P = str(Pmin)+'-'+str(Pmax)
    if PHImin == PHImax:
        PHI = str(PHImin)
    else:
        PHI = str(PHImin)+'-'+str(PHImax)

    title = f"ID: {ID}, {author}\nT={T} K, P={P} bar, $\Phi$={PHI}"
    return author, title



def get_SootTargets(my_sciexpem, AllExecs, fuel, exp_type):
    """
    :return: appends soot targets to standard targets.
    """
    # This function may be useful for biomass and plastics when included to SciExpeM

    listExp = []

    Experiments = my_sciexpem.filterDatabase(model_name='Experiment', fuels = fuel, status = 'verified', experiment_type = exp_type) # da modificare
    listExp = [j.id for j in Experiments]
    list_list_data_columnsPerFuel = [j.experiment.data_columns for j in AllExecs if j.experiment.id in listExp]
    list_data_columnsPerFuel = [item for sublist in list_list_data_columnsPerFuel for item in sublist]

    special_targets = [i.name for i in list_data_columnsPerFuel]
    special_targets = list(set(special_targets))
    special_targets = [i for i in special_targets if i != 'temperature' and i != 'residence time' \
                    and i != 'uncertainty' and i != 'ignition delay' and i != 'composition' and i != 'distance']
    special_targets = sorted(special_targets)

    # A smoother alternative to get special_targets is reported below, but it is extremely low to access i.name from SciExpeM database
    # special_targets = [i.name for i in list_data_columns if i.name != 'composition and i.name != 'temeprature' ...]

    return special_targets, list_data_columnsPerFuel



def get_listExpSpecialTargets(AllExecs, list_data_columnsPerFuel, target):
    """
    :return: appends soot targets to standard targets.
    """
    # This function may be useful for biomass and plastics when included to SciExpeM

    list_data_columnsPerFuelAndTarget = []
    for i in range(len(list_data_columnsPerFuel)):
        if list_data_columnsPerFuel[i].name == target: list_data_columnsPerFuelAndTarget.append(list_data_columnsPerFuel[i])

    listExp = []
    for i in range(len(list_data_columnsPerFuelAndTarget)):
        for k in range(len(AllExecs)):
            if list_data_columnsPerFuelAndTarget[i] in AllExecs[k].experiment.data_columns: 
                listExp.append(AllExecs[k].experiment.id)
                break
    
    list_Exp = list(OrderedDict.fromkeys(list_Exp))
    return listExp



def get_printmessaggio(start_message='PDF file created:',print_msg=True):
    lista_frasi = ['there is no I in a team', 'bears are not dangerous','sciabola!', 'scioabboloneee', 'puuuuh', 'yo nigz!', \
                    'do you live close to panda region?', 'rosso di sera, anghe de madina','amaskioooo',\
                    'chiacchiere, chiacchiere politiche', 'prova a ricompilare in python', 'is radiation true?', \
                    'alessandro!', 'aghislooooov', 'daje!', 'vesisssss ... ahahaahahahahha', "steve's alive!", \
                    'reminder: assumere software developer', 'maneskin > rolling stones', 'bebi camomi, camon', \
                    'oggetto mail: aggiornamento', 'sospensione servizio ritiro rifiuti SEDE MANCINELLI', 'chiavi in portineria MANCINELLI', \
                    'dear Professor Undear', 'the CRACK mechansim was used in this work', \
                    #"/lib64/libc.so.6: version `GLIBC_2.14' not found (required by /software/chimica2/tools/gcc/gcc-13.2.0/lib64/libstdc++.so.6)", \
                    "errore. Spegnere e Riaccendere", "Andrea! Abbiamo un nuovo tesista sul soot, non è che gli fai vedere velocemente come funziona?", \
                    "scappa alla trappola, la pornografia uccide",'Formazione uso DIISOCIANATI - corso DCMC online',
                    #'You are cordially invited to the following Virtual Seminars. These seminars are related to the mandatory course Chemical Engineering Frontiers (5 credits).', \
                    '-Tu hai preso? -Due chili e sei di tomahawk. - Sono 100 euro, grazie', 'andlea', 'franzesko','andrea dobbiamo parlare',
                    "URGENTE Fermo impianto cappe edificio 8 Sede Mancinelli"]
                    #,"Dear Colleague, \nI am writing you to tell that tomorrow I'll withdraw from my PhD Project. For this reason, I'll not be anymore your PhD Representative. \n It had been a difficult, but necessary, decision. \n Thank you very much for your support. \n I wish you all the best and good luck with your research!"]

    messaggio = choice(lista_frasi) # secrets library should be the closest to truly random generation
    if print_msg:
        print(start_message + messaggio)
    else:
        return start_message + messaggio

    # return ()

def goodbye_message(header=None):
    '''    
    header==None does not print any header nor reorganizes the sentence
    header=='' will employ the default one '|**********|'
    '''
    msg=get_printmessaggio(start_message='',print_msg=False)

    if header=='':
        header="|********************************************|"
    
    if header==None:
        header=''
        print(msg)
    else:
        
        print("\n"+header)        
        line2p=center_line2write(msg,len(header))
        print(line2p)

        print(header)

def center_line2write(line2write,max_length=1000):
    l2w=deepcopy(line2write)
    lcentered=''
    lh=max_length-2    
    while len(l2w)>lh:
        sttemp=l2w[:lh]
        sttemp=sttemp[:sttemp.rfind(" ")]
        i_to_center=int((lh-len(sttemp))/2)
        line2p=' '*int(i_to_center)+sttemp
        lcentered=lcentered+line2p+"\n"
        l2w=l2w.replace(sttemp,'')
        if l2w.find(" ")<0:
            break
    lcentered=lcentered[:-1]
    i_to_center=max(0,int((lh-len(l2w))/2))
    line2p=' '*int(i_to_center)+l2w

    return line2p
