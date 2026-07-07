from SciExpeM_API.SciExpeM import SciExpeM
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.ticker as mtick
import math
import os
import warnings
import plot_functions
from collections import OrderedDict

#import time

warnings.filterwarnings('ignore')

my_sciexpem = SciExpeM(username='YOUR_USERNAME', password='YOUR_PASSWORD', secure=False, port=8080)

#ID_ChemModel = 599 # 566 with soot,  567 without soot
ID_ChemModels = [682, 585, 681, 614]
labels = ['C3V4.0.1', 'C3V3','C3V4.0.1', 'C3V3']#,'','','','','']
ID_ChemModels = [871, 585,]
labels = ['C3V4.0.1', 'C3V3',]  # ,'','','','','']

#exps_type =  ['outlet concentration measurement']
exps_type =  ['ignition delay measurement']
              # 'ignition delay measurement', 'laminar burning velocity measurement']
              # 'burner stabilized flame speciation measurement', 'jet stirred reactor measurement', \
              # 'outlet concentration measurement', 'concentration time profile measurement', \
              # 'ignition delay measurement', 'laminar burning velocity measurement']

fuels = ['C5H6','C6H6','C7H8','O-XYLENE', 'M-XYLENE', 'P-XYLENE']          # fill with list of desired fuels. If empty all fuels are retrieved
# fill with list of desired fuels. If empty all fuels are retrieved
fuels = ['O-XYLENE', 'M-XYLENE', 'P-XYLENE', 'C6H5OH']
# if a mixture has to be included in the report, it must be specified as in the following example: fuels = [["C6H6","C3H4-P"], ['C6H6']]

targets = []            # fill with list of desired targets (chemical species). If empty all targets are retrieved
special_targets = []    # fill with list of desired special targets (not chemical species), e.g., soot volume fraction. If empty all special targets are retrieved 
preferred_order_species = [] #['NC7H16', 'O2','C7H14-1', 'C7H14-2', 'C7H14-3', 'CH4', 'CO', 'CO2', 'H2', 'H2O','C2H2', 'C2H4', 'C2H4O', 'C2H5CHO', 'C2H5OH','CH2O', 'CH3CHO', 'CH3CO2H', 'CH3COCH3', 'CH3O2H', 'CH3OH',  'HOCHO', 'C2H6', 'C3H4-A', 'C3H4-P', 'C3H6', 'C3H6O', 'C3H7CHO', 'C3H8', 'C4H6', 'C4H6O2', 'C4H8-1', 'C4H8-2-CIS', 'C4H8-2-T','IC4H8', 'C4H8O', 'C4H9CHO', 'LC5H8-13', 'NC5H10','C5H10-2-C', 'C5H10-2-T', 'C5H8O2',    'NC6H12',  'THF-2ETHYL-5METHYL', 'THF-2PROPYL']
species_to_be_removed = [] #['C3H2','BIN1B','C10H10-12','C10H7CH3','C14H10','C4H8-1']
# parameters for figures
#savepath = '/Users/alessandropegurri/Desktop/fuels/report'
# creare in un path a piacere la cartella 'report',
savepath = r'/Users/lpratalimaffei/Library/CloudStorage/OneDrive-PolitecnicodiMilano/Luna/Universita/RICERCA/OPENSMOKE/MECCANISMI/2024_CONVERGE_REBUTTAL'
# contenente le seguenti sottocartelle (che verranno riempite automaticamente con i file PDF del report):
# IDT, LFS, flame_speciations, outlet_speciations, time_speciations, JSR_speciations
OverwriteSavedPDFfile = True  # se True sovrascrive PDF già creati in precedenza
RemoveEmptyPDFfile = False    # se True rimuove PDF vuoti, ad esempio per un target di un fuel non simulato con il modello selezionato
IncludeSootTargets = False    # se True vengono incluse soot volume fraction, soot diameters, ecc, nei target standard, ossia le specie chimiche 

cm = 1/2.54
Nplots = 16     # Nplots for each pdf page, must be perfect square (e.g., 9, 16, 25, 36, ...)
color = ['k','k','k','k','b','b','b','b','r','r','r','r','g','g','g','g',]
linstyle = ['-','--','-','--','-','--','-.',':','-','--','-.',':','-','--','-.',':']
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
    #s_time = time.time()
    fuels, targets = plot_functions.get_fuels_targets(AllExecs, fuels, targets, list_data_columns)
    #e_time = time.time()
    #cpu_time = "{:.1e}".format(e_time-s_time)
    #print(f'{cpu_time} s to extract all fuels and targets')

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
        if len(fuel) ==1 :
            fuel_savename = fuel[0]
        else:
            fuel_savename = "_".join(fuel)
        if OverwriteSavedPDFfile == False and os.path.exists(os.path.join(savepath,exp_name,f"{fuel_savename}_{exp_name}.pdf")): continue
        
        print ('\n*** Plotting', exp_type, 'for fuel', fuel)
        if not os.path.exists(os.path.join(savepath,exp_name)):
            os.makedirs(os.path.join(savepath,exp_name))
        if len(labels) > 1:
            pdf = PdfPages(os.path.join(savepath,exp_name,f"{fuel_savename}_{exp_name}_{labels[1]}_lbl.pdf")) 
        else:
            pdf = PdfPages(os.path.join(savepath,exp_name,f"{fuel_savename}_{exp_name}_{labels[0]}_lbl.pdf")) 

        savepdf = False
        #s_fuel_time = time.time()

        if IncludeSootTargets == True:
            special_targets, list_data_columnsPerFuel = plot_functions.get_SootTargets(my_sciexpem, AllExecs, fuel, exp_type)       
        for i in special_targets: targets.append(i)
        targets = list(set(targets))    # per evitare duplicati a ogni for-cycle fatto sui fuels
        targets = sorted(targets)
        preferred_order_species_new = [sp if sp !='fuel' else fuel[0] for sp in preferred_order_species]
        preferred_order_species_new = [sp for sp in preferred_order_species_new if sp in targets]
        targets = preferred_order_species_new+targets
        targets = list(OrderedDict.fromkeys(targets))
        targets = [x for x in targets if x not in species_to_be_removed]



        for target in targets:

            # print inchi
            #   spx = my_sciexpem.filterDatabase(model_name='Species', preferredKey = target)
            #   print (target, ' ', spx[0].InChI)

            if IncludeSootTargets == True and target in special_targets:
                listExp = plot_functions.get_listExpSpecialTargets(AllExecs, list_data_columnsPerFuel, target)
            else: listExp = plot_functions.get_listExp(my_sciexpem, AllExecs, fuel, exp_type, target, list_list_data_columns, list_data_columns)

            if len(listExp) == 0:
                #print ('\t 0 executions for this target with model', ID_ChemModel)
                continue
            else: 
                print (f'\t Target: {target} - {len(listExp)} executions found. ID-experiments:')
                savepdf = True

            # calcola numero di pagine, ciascuna con Nplots figure
            Nsubplots = math.ceil(len(listExp)/Nplots)

            # separa listExp in sottoliste (una pagina di file PDF per ogni sottolista)
            exp_split_rows = [listExp[i:i+Nplots] for i in range(0,len(listExp),Nplots)]

            for i in range(1,Nsubplots+1):
                fig, ax = plt.subplots(figsize=(32*cm,32*cm),tight_layout=True)
                fig.suptitle(target,fontsize=fs*2)
                ax.remove() 

                for idj, j in enumerate(exp_split_rows[i-1]):
                    print(f'\t\t{j}')
                    # filtra Exp, Exec e FilePaper con fuel e exp-type selezionati
                    Exp = my_sciexpem.filterDatabase(model_name='Experiment', id = j)
                    if Exp[0].file_paper != None:
                        FilePaper = my_sciexpem.filterDatabase(model_name='FilePaper', id = Exp[0].file_paper.id)

                    # estrae x_exp, y_exp, e y_exp_unc
                    ID = j
                    x_exp, y_exp, y_unc_abs, warn_exp = plot_functions.get_xyexp(my_sciexpem, Exp, exp_type, ID, target)
                    if type(x_exp) == int: continue

                    
                    

                    # estrae proprietà dell'esperimento
                    author, title = plot_functions.get_expprop(Exp, FilePaper, ID)
                    
                    # plotta singolo subplot (uno per pagina)
                    plt.subplot(int(math.sqrt(Nplots)),int(math.sqrt(Nplots)),idj+1)
                    if len(y_unc_abs)>0:
                        plt.errorbar(x_exp,y_exp, yerr=y_unc_abs, fmt = 'o', markersize = 6, capsize=3, elinewidth=1, capthick=1, c=color[0], mfc = 'none')
                    else:
                        plt.scatter(x_exp,y_exp, edgecolor=color[0], facecolor = 'none') # plt.scatter non funziona (forse) per plottare le errorbars

                    warn_sim_final = False
                    y_sim_max = 0

                    # ciclo su ID chem models
                    for idI, ID_ChemModel in enumerate(ID_ChemModels):
                        Exec = my_sciexpem.filterDatabase(model_name='Execution', chemModel = ID_ChemModel, experiment = j)
                        if Exec == []:
                            print(f'\t\tWARNING: exp {j} has no simulations with model {ID_ChemModel}')
                            continue
                        # estrae e ordina x_sim e y_sim
                        x_sim, y_sim, warn_sim = plot_functions.get_xysim(Exec,exp_type,target)
                        if warn_sim == True:
                            warn_sim_final = True
                        plt.plot(x_sim,y_sim, linstyle[idI], c=color[idI], label = labels[idI])
                        y_sim_max = max(y_sim_max,max(y_sim))
                        if y_sim_max != 0:
                            y_sim_max = 10 ** math.ceil(math.log10(y_sim_max))

                    if warn_exp == True:
                        title = title+'\nFake EXP' # per esperimenti con speciazione di somme di specie (e.g., "CxHy_A+CxHy_B [mole fraction]")
                    if warn_sim == True:
                        title = title+'\nNo sim'   # per experimenti con speciazione misurata ma non simulata (e.g., il modello non contiene la specie misurata CxHy)

                    # calcola caratteristiche degli assi dei plot
                    x_range, y_range, xlabel, ylabel, yscale, tick_positions = plot_functions.get_xyrange(Exp,y_sim_max, x_exp,y_exp,extra_x,extra_y,exp_type, target)

                    plt.xlabel(xlabel,fontsize=fs)
                    plt.ylabel(ylabel,fontsize=fs)
                    plt.title(title,fontsize = fs,fontweight='bold')
                    plt.xticks(fontsize=fs)
                    plt.yscale(yscale)
                    plt.legend(fontsize=5)
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

        #e_fuel_time = time.time()
        #cpu_fuel_time = "{:.1e}".format(e_fuel_time-s_fuel_time)
        #print(f'{cpu_fuel_time} s to save all plots for fuel {fuel}')
        pdf.close()
        # if RemoveEmptyPDFfile == True and savepdf == False: os.remove(os.path.join(savepath,exp_name,f"{fuel_savename}_{exp_name}.pdf")) # remove PDF file if empty
        plot_functions.goodbye_message('')
        
