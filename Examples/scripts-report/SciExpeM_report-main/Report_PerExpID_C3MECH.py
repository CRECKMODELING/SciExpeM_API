from SciExpeM_API.SciExpeM import SciExpeM
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.ticker as mtick
import math
import os
import pandas as pd
import warnings
import sys
sys.path.append(
    r"/Users/lpratalimaffei/Library/CloudStorage/OneDrive-PolitecnicodiMilano/Luna/Universita/RICERCA/SCIEXPEM/scripts-report/SciExpeM_report-main")
import plot_functions
from collections import OrderedDict

#import time

warnings.filterwarnings('ignore')

my_sciexpem = SciExpeM(username='YOUR_USERNAME',
                       password='YOUR_PASSWORD', port=8080, secure=False)

#ID_ChemModel = 599 # 566 with soot,  567 without soot
ID_ChemModels = [738, 741, 739]
labels = ['C3V4-OMEs', 'CRECK-OMEs', 'C3V4-OMEs 436 sp']#,'','','','','']
ID_ChemModels = [740, 741,]
labels = ['C3V4-OMEs', 'CRECK-OMEs', ]#,'','','','','']
#exps_type =  ['outlet concentration measurement']
list_exps = {'jet stirred reactor measurement': [2400,
                                                 2415,
                                                 3254,
                                                 3620,
                                                 3621,
                                                 3622,
                                                 3623,
                                                 3626,
                                                 3627,
                                                 3628,
                                                 3631,
                                                 3644,
                                                 3673,
                                                 3283,
                                                 3284,
                                                 3287,
                                                 3633,
                                                 3634,
                                                 3635,
                                                 3636,
                                                 3637,
                                                 3638,
                                                 3639,
                                                 3640,
                                                 3641,
                                                 3642,
                                                 3643,
                                                 3669,
                                                 3670,]} 
list_exps = {'jet stirred reactor measurement':[3973	,
3975	,
3977	,
3978	,
	
3979	,
3980	,
3981	,
3982	,
3983	,
3984	,
3985	,]}
exps_type = ['jet stirred reactor measurement']
              # 'burner stabilized flame speciation measurement', 'jet stirred reactor measurement', \
              # 'outlet concentration measurement', 'concentration time profile measurement', \
              # 'ignition delay measurement', 'laminar burning velocity measurement']

# fill with list of desired fuels. If empty all fuels are retrieved
fuels = ['DMM']
fuels = ['OME2', 'OME3']
# if a mixture has to be included in the report, it must be specified as in the following example: fuels = [["C6H6","C3H4-P"], ['C6H6']]

targets =  []
special_targets = []    # fill with list of desired special targets (not chemical species), e.g., soot volume fraction. If empty all special targets are retrieved 
# ['NC7H16','O2','CO','CO2','CH4','C7H14-1','C7H14-2','C7H14-3',] #['C6H6','H2','CH4','C2H2', 'C2H4', 'C2H6', 'C3H3','C3H4-P','C3H4-A', 'C3H6','C4H2','C4H4','C5H6','C5H5','C6H2','C6H5', 'CYC6H4','C6H5C2H3','C6H5C2H','C7H8','INDENE', 'INDENYL','C10H8','FLUORENE']
preferred_order_species = ['DMM', 'OME2', 'OME3', 'OME4']
species_to_be_removed = [] #['C3H2','BIN1B','C10H10-12','C10H7CH3','C14H10','C4H8-1','IC4H10','C6H5C2H2C6H5','C6H5C2H4C2H','C6H4O2-P','C18H12-P', 'AC10H8','ACENAPH','BIPHENYLC2H','BIPHENYLENE','C10H6', 'C10H6(C2H)2','IC4H8','C6H5CCC6H5','C5H5O','C5H4O','C8H2','CYC6H8', 'C10H7C2H-1','C10H7C2H3-1','C10H7C6H5-1','C12H7C2H-1','C12H7C2H-5','C13H8CH2','C14H10-A','C14H12','M-TERPH', 'C18H12-A','C18H12-C','C4H6-1,','C4H6-12','C4H6-2','C4H8-2-T','C6H5CCCH3','C9H6CH2','C9H7CH3, 1','FLUORANTHENE', 'C4H6-1']
# parameters for figures

ID_ChemModels = [1190, 1189, ]
labels = ['newc2', 'oldc2']  # ,'','','','','']
mechs = '_'.join(labels)
# exps_type =  ['outlet concentration measurement']
list_exps = {'concentration time profile measurement': [4061, 4062, 4088, 4480, 4065, 4066, 4067,  4127, 4128, 4129, 4130, 4131, 4132,
                                                         ],  # 4068, 2972
           #  'outlet concentration measurement': [ 4087, 4086, 4085, ],
           #  'jet stirred reactor measurement': [3885,
           #                                      3880,
           #                                      3883,
           #                                      3884,
           #                                      3881,
           #                                      3882]
             }

exps_type = [
             'concentration time profile measurement']
# 'burner stabilized flame speciation measurement', 'jet stirred reactor measurement', \
# 'outlet concentration measurement', 'concentration time profile measurement', \
# 'ignition delay measurement', 'laminar burning velocity measurement']

# fill with list of desired fuels. If empty all fuels are retrieved
fuels = ['C2H2', 'C2H4', 'C3H4-A', 'C3H4-P', 'C4H6', 'C5H6', 'C6H6', 'C7H8']
fuels = ['C2H2', 'C4H2', 'C4H6']
# if a mixture has to be included in the report, it must be specified as in the following example: fuels = [["C6H6","C3H4-P"], ['C6H6']]

savepath = r'/Users/lpratalimaffei/Library/CloudStorage/OneDrive-PolitecnicodiMilano/Luna/Universita/RICERCA/OPENSMOKE/MECCANISMI/2026_CONVERGE/'
# contenente le seguenti sottocartelle (che verranno riempite automaticamente con i file PDF del report):
# IDT, LFS, flame_speciations, outlet_speciations, time_speciations, JSR_speciations
OverwriteSavedPDFfile = True  # se True sovrascrive PDF già creati in precedenza
RemoveEmptyPDFfile = False    # se True rimuove PDF vuoti, ad esempio per un target di un fuel non simulato con il modello selezionato
IncludeSootTargets = False    # se True vengono incluse soot volume fraction, soot diameters, ecc, nei target standard, ossia le specie chimiche 

cm = 1/2.54
Nplots = 16     # Nplots for each pdf page, must be perfect square (e.g., 9, 16, 25, 36, ...)
color = ['k','k','k','k','b','b','b','b','r','r','r','r','g','g','g','g',]
linstyle = ['-','--',':',':','-','--','-.',':','-','--','-.',':','-','--','-.',':']
fs = 8          # fontsize
extra_x = 0.2   # percentage for extra x-range with respect to max(x-exp)-min(x-exp)
extra_y = 0.2   # percentage for extra y-range with respect to max(y-exp)-min(y-exp)

AllExecs = []
for ID_ChemModel in ID_ChemModels: 
    AllExecs = AllExecs+my_sciexpem.filterDatabase(model_name='Execution', chemModel = ID_ChemModel)
list_list_data_columns = [j.experiment.data_columns for j in AllExecs]
list_data_columns = [item for sublist in list_list_data_columns for item in sublist]         
print ('*** Creating report for models', ID_ChemModels)
print ('\t', len(list_list_data_columns), 'experiments found')
print ('\t OverwriteSavedPDFfile =', OverwriteSavedPDFfile)
print ('\t RemoveEmptyPDFfile = ', RemoveEmptyPDFfile)
print ('\t IncludeSootTargets = ', IncludeSootTargets)

for exp_type in exps_type:
    
    if exp_type == 'ignition delay measurement' or exp_type == 'laminar burning velocity measurement':
        targets = [exp_type]
    else:
        targets = []
        
    fuels, targets = plot_functions.get_fuels_targets(AllExecs, fuels, targets, list_data_columns)

    match exp_type:
        case 'ignition delay measurement':
            exp_name = 'IDT'
        case 'laminar burning velocity measurement':
            exp_name = 'LFS'
        case 'jet stirred reactor measurement':
            exp_name = 'JSR_speciations'
        case 'outlet concentration measurement':
            exp_name = 'outlet_speciations'
        case 'concentration time profile measurement':
            exp_name = 'time_speciations'
        case 'burner stabilized flame speciation measurement':
            exp_name = 'flame_speciations'

    # loop for each fuel
    for fuel in fuels:
        """
        if len(fuel) ==1 :
            fuel_savename = fuel[0]
        else:
            fuel_savename = "_".join(fuel)
        if OverwriteSavedPDFfile == False and os.path.exists(os.path.join(savepath,exp_name,f'{fuel_savename}_{exp_name}.pdf')): continue
        
        print ('\n*** Plotting', exp_type, 'for fuel', fuel)
        if not os.path.exists(os.path.join(savepath,exp_name)):
            os.makedirs(os.path.join(savepath,exp_name))

        if IncludeSootTargets == True:
            special_targets, list_data_columnsPerFuel = plot_functions.get_SootTargets(my_sciexpem, AllExecs, fuel, exp_type)       
        for i in special_targets: targets.append(i)
        
        """
        targets = list(set(targets))
        targets = sorted(targets)
        preferred_order_species_new = [sp if sp !='fuel' else fuel[0] for sp in preferred_order_species]
        preferred_order_species_new = [sp for sp in preferred_order_species_new if sp in targets]
        targets = preferred_order_species_new+targets
        targets = list(OrderedDict.fromkeys(targets))
        targets = [x for x in targets if x not in species_to_be_removed]

        """
        listExp = []
        for target in targets:

            if IncludeSootTargets == True and target in special_targets:
                listExpPerTarget = plot_functions.get_listExpSpecialTargets(AllExecs, list_data_columnsPerFuel, target)
            else: 
                listExpPerTarget = plot_functions.get_listExp(my_sciexpem, AllExecs, fuel, exp_type, target, list_list_data_columns, list_data_columns)

            if len(listExpPerTarget) == 0:
                #print ('\t 0 executions for this target with model', ID_ChemModel)
                continue
            else: 
                print (f'\t Target: {target} - {len(listExpPerTarget)} executions found.')
                savepdf = True
            listExp = listExp + listExpPerTarget

        listExp = list(set(listExp))
        print(listExp, targets)
        """              
        # check that exp has no profiles
        
        print(exp_type, list_exps[exp_type], targets)
        pdf = PdfPages(os.path.join(savepath,exp_name,f'{fuel}_{exp_name}.pdf'))       
        for j in list_exps[exp_type]:

            print(f'\t\t{j}')
            # filtra Exp, Exec e FilePaper con fuel e exp-type selezionati
            Exp = my_sciexpem.filterDatabase(model_name='Experiment', id = j)
            if Exp[0].file_paper != None:
                FilePaper = my_sciexpem.filterDatabase(model_name='FilePaper', id = Exp[0].file_paper.id)
            #check if there are profiles
            dg_labels = [el.dg_label for el in Exp[0].data_columns]
            has_profiles = bool(any('history' in label for label in dg_labels))

            ID = j
            fig, ax = plt.subplots(figsize=(32*cm,32*cm),tight_layout=True)
            author, title = plot_functions.get_expprop(Exp, FilePaper, ID)
            fig.suptitle(title,fontsize=fs*2)
            ax.remove() 
            # REORDER TARGETS BASED ON MAX CONCENTRATION
            if exp_type not in ['ignition delay measurement','laminar burning velocity measurement']:
                targets_new = pd.Series(0, index=targets)
                for target in targets:
                    _, y_exp, _, _ = plot_functions.get_xyexp(my_sciexpem, Exp, exp_type, ID, target)
                    if (type(y_exp) == int): continue
                    elif len(y_exp) < 2: continue
                    targets_new[target] = max(y_exp)
                targets = list(targets_new.sort_values(ascending = False).index)
                # print(targets_new, targets)
            # estrae x_exp, y_exp, e y_exp_unc
            idjj=-1
            for target in targets:
                print(target)
                x_exp, y_exp, y_unc_abs, warn_exp = plot_functions.get_xyexp(my_sciexpem, Exp, exp_type, ID, target)
                if (type(x_exp) == int): continue
                elif (len(x_exp) == 2): continue
                else: idjj=idjj+1

                if (idjj == Nplots):
                    pdf.savefig(fig)
                    fig, ax = plt.subplots(figsize=(32*cm,32*cm),tight_layout=True)
                    author, title = plot_functions.get_expprop(Exp, FilePaper, ID)
                    fig.suptitle(title,fontsize=fs*2)
                    ax.remove()
                
                # plotta singolo subplot
                if idjj < Nplots: npag = 1
                elif idjj < 2*Nplots: npag = 2
                elif idjj < 3*Nplots: npag = 3
                print(idjj, Nplots, npag)
                plt.subplot(int(math.sqrt(Nplots)),int(math.sqrt(Nplots)),idjj+1-Nplots*(npag-1))
                if len(y_unc_abs)>0:
                    plt.errorbar(x_exp,y_exp, yerr=y_unc_abs, fmt = 'o', markersize = 6, capsize=3, elinewidth=1, capthick=1, c=color[0], mfc = 'none')
                else:
                    plt.scatter(x_exp,y_exp, edgecolor=color[0], facecolor = 'none') # plt.scatter non funziona (forse) per plottare le errorbars
                    print('exp data', 'ID {}'.format(j))
                    #print(pd.DataFrame(y_exp, index=x_exp))
                warn_sim_final = False
                y_sim_max = 0

                # ciclo su ID chem models
                for idI, ID_ChemModel in enumerate(ID_ChemModels):
                    Exec = my_sciexpem.filterDatabase(model_name='Execution', chemModel = ID_ChemModel, experiment = j)
                    if Exec == []:
                        print(f'\t\tWARNING: exp {j} has no simulations with model {ID_ChemModel}')
                        continue
                    if Exec[0].simulation_results[0] == {}:
                        print(f'\t\tWARNING: exec of exp {j} with model {ID_ChemModel} is empty - probably not ended yet ')
                        continue                        
                    # estrae e ordina x_sim e y_sim
                    x_sim, y_sim, warn_sim = plot_functions.get_xysim(Exec,exp_type,target)
                    if warn_sim == True:
                        warn_sim_final = True
                    # if simul with profiles: plot the x_exp
                    if has_profiles is True:
                        if len(x_exp) == len(x_sim):
                            print('*Warning: exp with profiles. plotting with x_sim = x_exp until bug will be fixed')
                            plt.plot(
                                x_exp, y_sim, linstyle[idI], c=color[idI], label=labels[idI])
                        else:
                            print(
                                '*Warning: exp with profiles, but x_exp and x_sim have different lengths, so x_sim (wrong) being used anyways')
                            plt.plot(
                                x_sim, y_sim, linstyle[idI], c=color[idI], label=labels[idI])
                    else:
                        plt.plot(x_sim,y_sim, linstyle[idI], c=color[idI], label = labels[idI])
                    #print(labels[idI], 'exp {}'.format(j))
                    #print(pd.DataFrame(y_sim, index=x_sim))
                    y_sim_max = max(y_sim_max,max(y_sim))
                    if y_sim_max != 0:
                        y_sim_max = 10 ** math.ceil(math.log10(y_sim_max))

                if warn_exp == True:
                    title = title+'\nFake EXP' # per esperimenti con speciazione di somme di specie (e.g., "CxHy_A+CxHy_B [mole fraction]")
                if warn_sim == True:
                    title = title+'\nNo sim'   # per experimenti con speciazione misurata ma non simulata (e.g., il modello non contiene la specie misurata CxHy)

                # calcola caratteristiche degli assi dei plot
                x_range, y_range, xlabel, ylabel, yscale, tick_positions = plot_functions.get_xyrange(Exp,y_sim_max, x_exp,y_exp,extra_x,extra_y,exp_type, target)

                title = target

                plt.xlabel(xlabel,fontsize=fs)
                plt.ylabel(ylabel,fontsize=fs)
                plt.title(title,fontsize = fs,fontweight='bold')
                plt.xticks(fontsize=fs)
                plt.yscale(yscale)
                plt.legend(fontsize=5)
                leg = plt.legend()
                leg.get_frame().set_linewidth(0.0)
                if exp_type != 'laminar burning velocity measurement':

                    plt.ylim(y_range)
                    plt.yticks(tick_positions, fontsize=fs)
                    ax = plt.gca()
                    if exp_type == 'ignition delay measurement':
                        ax.set_yticklabels(tick_positions, minor=True)
                    else:
                        ax.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.1e'))

                if type(x_range) != list:
                    plt.xlim(x_range) # per casi con warn_exp

            # salva singolo subplot su una pagina del file PDF
            pdf.savefig(fig)
        pdf.close()

        # if RemoveEmptyPDFfile == True and savepdf == False: os.remove(os.path.join(savepath,exp_name,f'{fuel_savename}_{exp_name}.pdf')) # remove PDF file if empty
        #plot_functions.goodbye_message('')
        
