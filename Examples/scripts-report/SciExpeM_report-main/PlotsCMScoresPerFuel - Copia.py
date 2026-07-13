import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib
import pandas as pd
import numpy as np
from matplotlib import gridspec
from collections import Counter
import os
from SciExpeM_API.SciExpeM import SciExpeM
import plot_functions

models = ['1','2ndO2Add','Abs','betaC','betaH','Class5','ConcEl','CycEth','init',
          'initH','ketoDec','ketoForm','LT_Iso','O2Add','QOOHDec','QOOHHO2']
models = ['1','QOOHHO2']
my_sciexpem = SciExpeM(username='YOUR_USERNAME', password='YOUR_PASSWORD')
path = r'D:\POLI\OPENSMOKE\ALKANES\NC7'
#loc = r'D:\POLI\OPENSMOKE\ALKANES\NC7\NATPROT-1.xlsx' # report downloaded from SciExpeM ('Analysis' section)
locs = [r'D:\POLI\OPENSMOKE\ALKANES\NC7\NATPROT-1.xlsx',
        r'D:\POLI\OPENSMOKE\ALKANES\NC7\NATPROT-QOOHHO2.xlsx',]

fuel = 'NC7H16'
colors = ['g','r','k','k','b','b','b','b','r','r','r','r','g','g','g','g',]
markers = ['o','x','.','v','^','<','>','1','2','3','4','8','s','p','P',',','h','+','*','D']
emptymarkers = ['x','.','v','^','<','>','1','2','3','4',',','+']
# Parameters for plots with too many targets
targets_length = 15
targets_count = 2
deltaT_interval = 100
fontsize = 8

print_sums = True
plots_report = True
plots_quartili = False

cm = 1/2.54
width = 20 #larghezza plots
height = 7 #altezza plots

Tmin_left = 250
Tmin_right = 3000
Tmin_N = 10
Tmax_left = 500
Tmax_right = 3000
Tmax_N = 10

Pmin_left = 0.8
Pmin_right = 102
Pmin_N = 10
Pmax_left = 0.8
Pmax_right = 102
Pmax_N = 10

Phimin_left = 0
Phimin_right = 2
Phimin_N = 5
Phimax_left = 0
Phimax_right = 2
Phimax_N = 5

def round_down_to_ten(number):
    return number // 10 * 10
def round_up_to_ten(number):
    number // 10 * 10
    return number + 10

plt.figure(figsize=(32*cm, 18*cm),tight_layout=True)
for ii, loc in enumerate(locs):
    data = pd.read_excel(loc, dtype=object)
    data = data.fillna('')

    # add columns to the dataframe
    #Phi min,Phi max,Pressure min,Pressure max,Temperature min,Temperature max
    data2 = pd.DataFrame(index=data.index,columns=['Pressure min','Pressure max', 'Temperature min', 'Temperature max', 'Phi min', 'Phi max'], dtype = float)
    for idx in data.index:
        phimin, phimax = data['Phi'][idx].split('(')[1].split(')')[0].split(', ')
        pmin, pmax = data['Pressure (Bar)'][idx].split('(')[1].split(')')[0].split(', ')
        tmin, tmax = data['Temperature (K)'][idx].split('(')[1].split(')')[0].split(', ')
        data2.loc[idx][['Pressure min','Pressure max', 
                    'Temperature min', 'Temperature max', 
                    'Phi min', 'Phi max']] = np.array([pmin, pmax, tmin, tmax, phimin, phimax], dtype = float)
    data = pd.concat([data, data2], axis=1)

    # filter fuels 
    # 1. find fuels by exp id.
    """
    expids = list(set(data['Exp SciExpeM ID'].values))
    ids = [my_sciexpem.filterDatabase(model_name='Experiment', id=int(idx))[0] for idx in expids]
    for idx in ids:
        fuels = plot_functions.find_fuels([idx])
        fuels = '+'.join(fuels)
        indices = data[data['Exp SciExpeM ID'] == idx.id].index
        data.loc[indices, 'Fuels'] = fuels

    # 2. filter data according to fuel 
    mask = (data['Fuels'] == fuel) | (data['Fuels'].str.contains(fuel + '+'))
    data = data[mask]
    """
    #separate negative CM
    neg = data[data['Score']<0]
    tot_neg = neg.shape[0]
    ID_neg = neg['Exp SciExpeM ID'].sort_values(ascending=True)
    data = data[data['Score']>0]

    #filter targets
    data_IDT = data[data['Target'].str.contains('tau',case=False)]
    data_LFS = data[data['Target']=='Speed']
    #data_spec = data[data['Target'].str.contains('_x',case=False)]
    data_spec = data[~data['Target'].str.contains('tau') & ~data['Target'].str.contains('Speed')]

    data_spec_fuel = data_spec[data_spec['Target']==fuel+'_x']
    data_spec_others = data_spec[data_spec['Target']!=fuel+'_x']

    data_spec_JSR = data_spec[data_spec['Reactor'].str.contains('stirred reactor')]
    data_spec_PFR = data_spec[data_spec['Reactor'].str.contains('flow reactor')]
    data_spec_ST = data_spec[data_spec['Reactor']=='shock tube']
    data_spec_flame = data_spec[data_spec['Reactor']=='flame']

    #evaluate
    n_IDT = data_IDT.shape[0]
    n_LFS = data_LFS.shape[0]
    n_spec_fuel = data_spec_fuel.shape[0]
    n_spec_others = data_spec_others.shape[0]
    n_spec_JSR = data_spec_JSR.shape[0]
    n_spec_PFR = data_spec_PFR.shape[0]
    n_spec_ST = data_spec_ST.shape[0]
    n_spec_flame = data_spec_flame.shape[0]

    Tmin_IDT = data_IDT['Temperature min'].min()
    Tmin_LFS = data_LFS['Temperature min'].min()
    Tmin_spec_JSR = data_spec_JSR['Temperature min'].min()
    Tmin_spec_PFR = data_spec_PFR['Temperature min'].min()
    Tmin_spec_ST = data_spec_ST['Temperature min'].min()
    Tmin_spec_flame = data_spec_flame['Temperature min'].min()

    Tmax_IDT = data_IDT['Temperature max'].max()
    Tmax_LFS = data_LFS['Temperature max'].max()
    Tmax_spec_JSR = data_spec_JSR['Temperature max'].max()
    Tmax_spec_PFR = data_spec_PFR['Temperature max'].max()
    Tmax_spec_ST = data_spec_ST['Temperature max'].max()
    Tmax_spec_flame = data_spec_flame['Temperature max'].max()

    Pmin_IDT = data_IDT['Pressure min'].min()
    Pmin_LFS = data_LFS['Pressure min'].min()
    Pmin_spec_JSR = data_spec_JSR['Pressure min'].min()
    Pmin_spec_PFR = data_spec_PFR['Pressure min'].min()
    Pmin_spec_ST = data_spec_ST['Pressure min'].min()
    Pmin_spec_flame = data_spec_flame['Pressure min'].min()

    Pmax_IDT = data_IDT['Pressure max'].max()
    Pmax_LFS = data_LFS['Pressure max'].max()
    Pmax_spec_JSR = data_spec_JSR['Pressure max'].max()
    Pmax_spec_PFR = data_spec_PFR['Pressure max'].max()
    Pmax_spec_ST = data_spec_ST['Pressure max'].max()
    Pmax_spec_flame = data_spec_flame['Pressure max'].max()

    Phimin_IDT = data_IDT['Phi min'].min()
    Phimin_LFS = data_LFS['Phi min'].min()
    Phimin_spec_JSR = data_spec_JSR['Phi min'].min()
    Phimin_spec_PFR = data_spec_PFR['Phi min'].min()
    Phimin_spec_ST = data_spec_ST['Phi min'].min()
    Phimin_spec_flame = data_spec_flame['Phi min'].min()

    Phimax_IDT = data_IDT['Phi max'].max()
    Phimax_LFS = data_LFS['Phi max'].max()
    Phimax_spec_JSR = data_spec_JSR['Phi max'].max()
    Phimax_spec_PFR = data_spec_PFR['Phi max'].max()
    Phimax_spec_ST = data_spec_ST['Phi max'].max()
    Phimax_spec_flame = data_spec_flame['Phi max'].max()

    CM_IDT = round(data_IDT['Score'].mean(),2)
    CM_LFS = round(data_LFS['Score'].mean(),2)
    CM_spec_fuel = round(data_spec_fuel['Score'].mean(),2)
    CM_spec_others = round(data_spec_others['Score'].mean(),2)
    CM_spec_JSR = round(data_spec_JSR['Score'].mean(),2)
    CM_spec_PFR = round(data_spec_PFR['Score'].mean(),2)
    CM_spec_ST = round(data_spec_ST['Score'].mean(),2)
    CM_spec_flame = round(data_spec_flame['Score'].mean(),2)

    #find mixtures
    #fuels = pd.Series(pd.concat([data['Fuel 1'],data['Fuel 2'],data['Fuel 3']]).unique())
    fuels = pd.Series(data['Fuels'].unique())
    mixtures = []
    for fuelsall in fuels.values:
        mixtures.extend((fuelsall.split('+')))
    mixtures = list(set(mixtures))

    if len(mixtures) > 1:
        mixtures.remove(fuel)

    #find species targets
    targets = pd.Series(data_spec['Target'].unique())
    targets = targets.str.replace('_x','')
    targets = [s for s in targets if ((s != fuel) | ('tau' not in s))]

    #tot
    tot_exp = pd.Series(data['Exp SciExpeM ID'].unique())
    tot_ID = len(tot_exp)
    tot_profiles = data.shape[0]
    tot_CM = round(data['Score'].mean(),2)

    #print CM table of a fuel
    if print_sums == True:
        print(f'\t\t\t\t\t\tT[K]\t\tP[bar]\t\tPhi')
        print(f'IDT ({n_IDT}-{CM_IDT})\t\t\t\t\t{Tmin_IDT}-{Tmax_IDT}\t{Pmin_IDT}-{Pmax_IDT}\t{Phimin_IDT}-{Phimax_IDT}')
        print(f'LFS ({n_LFS}-{CM_LFS})\t\t\t\t\t{Tmin_LFS}-{Tmax_LFS}\t{Pmin_LFS}-{Pmax_LFS}\t{Phimin_LFS}-{Phimax_LFS}')
        print(f'Speciation\t\tJSR ({n_spec_JSR}-{CM_spec_JSR})\t\t{Tmin_spec_JSR}-{Tmax_spec_JSR}\t{Pmin_spec_JSR}-{Pmax_spec_JSR}\t{Phimin_spec_JSR}-{Phimax_spec_JSR}')
        print(f'\t\t\tPFR ({n_spec_PFR}-{CM_spec_PFR})\t\t{Tmin_spec_PFR}-{Tmax_spec_PFR}\t{Pmin_spec_PFR}-{Pmax_spec_PFR}\t{Phimin_spec_PFR}-{Phimax_spec_PFR}')
        print(f'Fuel* ({n_spec_fuel}-{CM_spec_fuel})\t\tST ({n_spec_ST}-{CM_spec_ST})\t\t{Tmin_spec_ST}-{Tmax_spec_ST}\t{Pmin_spec_ST}-{Pmax_spec_ST}\t{Phimin_spec_ST}-{Phimax_spec_ST}')
        print(f'Others** ({n_spec_others}-{CM_spec_others})\tFlame ({n_spec_flame}-{CM_spec_flame})\t\t{Tmin_spec_flame}-{Tmax_spec_flame}\t{Pmin_spec_flame}-{Pmax_spec_flame}\t{Phimin_spec_flame}-{Phimax_spec_flame}\n')
        print(f'*Mixtures: {mixtures}')
        print(f'**{targets}\n')
        print(f'{tot_ID} experiment-IDs')
        print(f'{tot_profiles} profiles\n')
        print(f'Average CM Score: {tot_CM}')
        print(f'Negative CM ({tot_neg}), IDs {ID_neg.to_string(index=False)}')

    #plots CM-points per target, T, P, phi of a fuel
    if plots_report == True:

        #plot targets
        data['Target'] = data['Target'].str.replace('.*tau.*','IDT',regex=True)
        data['Target'] = data['Target'].str.replace('Speed','LFS',regex=True)
        data['Target'] = data['Target'].str.replace('_x','')

        for idx in data_spec.index:
            data_spec.loc[idx,'Target'] = data_spec['Target'][idx].replace('_x','')


        if data_spec['Target'].unique().size > targets_length:
            c = Counter(data_spec['Target'])
            selected_elements = [element for element, count in c.items() if count < targets_count]
            data['Target'] = ['Others' if item in selected_elements else item for item in data['Target']]

        x_labels = data['Target'].unique()
        firsts = ['IDT', 'LFS', fuel]
        data['Sort_Order'] = data['Target'].apply(lambda x: (x not in firsts, x))
        data = data.sort_values(by='Sort_Order').drop(columns=['Sort_Order'])

        ax1 = plt.subplot(5,1,1)
        plt.title('Target',fontsize=14)
        plt.ylim(0,1)
        plt.grid(True)
        if data_spec['Target'].unique().size > targets_length:
            sns.scatterplot(x='Target',y='Score',data=data,marker=markers[ii],facecolors='none'*(markers[ii] not in emptymarkers)+colors[ii]*(markers[ii] in emptymarkers),edgecolors='none'*(markers[ii] in emptymarkers)+colors[ii]*(markers[ii] not in emptymarkers),)
            plt.xticks(fontsize=fontsize)
        else: 
            sns.scatterplot(x='Target',y='Score',data=data,marker=markers[ii],facecolors='none'*(markers[ii] not in emptymarkers)+colors[ii]*(markers[ii] in emptymarkers),edgecolors='none'*(markers[ii] in emptymarkers)+colors[ii]*(markers[ii] not in emptymarkers),)

        #plot Tmin
        ax2 = plt.subplot(5,1,2)
        plt.title('minimum Temperature',fontsize=14)
        plt.ylim(0,1)
        plt.xlim(data['Temperature min'].min(), data['Temperature max'].max())
        plt.grid(True)
        sns.scatterplot(x='Temperature min',y='Score',data=data,marker=markers[ii],facecolors='none'*(markers[ii] not in emptymarkers)+colors[ii]*(markers[ii] in emptymarkers),edgecolors='none'*(markers[ii] in emptymarkers)+colors[ii]*(markers[ii] not in emptymarkers),)
        Tminn = round_down_to_ten(data['Temperature min'].min())
        Tmaxx = round_down_to_ten((data['Temperature max'].max()))
        NNN = int((Tmaxx-Tminn)/deltaT_interval) + 1
        tick_positions = np.linspace(Tminn, Tminn + NNN*deltaT_interval, NNN+1)
        plt.xticks(tick_positions)
        
        #plot Tmax
        ax3 = plt.subplot(5,1,3)
        plt.title('maximum Temperature',fontsize=14)
        plt.ylim(0,1)
        plt.xlim(data['Temperature min'].min(), data['Temperature max'].max())
        plt.grid(True)
        sns.scatterplot(x='Temperature max',y='Score',data=data,marker=markers[ii],facecolors='none'*(markers[ii] not in emptymarkers)+colors[ii]*(markers[ii] in emptymarkers),edgecolors='none'*(markers[ii] in emptymarkers)+colors[ii]*(markers[ii] not in emptymarkers),)
        plt.xticks(tick_positions)

        #plot Pmin
        ax4 = plt.subplot(5,3,10)
        plt.title('p = 0 - 5 bar')
        plt.xlim(0,5)
        plt.ylim(0,1)
        plt.grid(True)
        sns.scatterplot(x='Pressure min',y='Score',data=data,marker=markers[ii],facecolors='none'*(markers[ii] not in emptymarkers)+colors[ii]*(markers[ii] in emptymarkers),edgecolors='none'*(markers[ii] in emptymarkers)+colors[ii]*(markers[ii] not in emptymarkers),)
        tick_positions = np.linspace(0, 5, 6)
        plt.xticks(tick_positions)
    
        ax5 = plt.subplot(5,3,11)
        plt.title('p = 5 - 50 bar')
        plt.xlim(5,50)
        plt.ylim(0,1)
        plt.grid(True)
        sns.scatterplot(x='Pressure min',y='Score',data=data,marker=markers[ii],facecolors='none'*(markers[ii] not in emptymarkers)+colors[ii]*(markers[ii] in emptymarkers),edgecolors='none'*(markers[ii] in emptymarkers)+colors[ii]*(markers[ii] not in emptymarkers),)
        tick_positions = np.linspace(5, 50, 10)
        plt.xticks(tick_positions)
        
        ax6 = plt.subplot(5,3,12)
        plt.title('p = 50 - 200 bar')
        plt.xlim(50,200)
        plt.ylim(0,1)
        plt.grid(True)
        sns.scatterplot(x='Pressure min',y='Score',data=data,marker=markers[ii],facecolors='none'*(markers[ii] not in emptymarkers)+colors[ii]*(markers[ii] in emptymarkers),edgecolors='none'*(markers[ii] in emptymarkers)+colors[ii]*(markers[ii] not in emptymarkers),)
        tick_positions = np.linspace(50, 200, 4)
        plt.xticks(tick_positions)

        #plot Phimin
        ax7 = plt.subplot(5,3,13)
        plt.title('Phi = 0 - 2',fontsize=14)
        plt.xlim(0,2)
        plt.ylim(0,1)
        plt.grid(True)
        sns.scatterplot(x='Phi min',y='Score',data=data,marker=markers[ii],facecolors='none'*(markers[ii] not in emptymarkers)+colors[ii]*(markers[ii] in emptymarkers),edgecolors='none'*(markers[ii] in emptymarkers)+colors[ii]*(markers[ii] not in emptymarkers),)
        tick_positions = np.linspace(0, 2, Phimin_N)
        plt.xticks(tick_positions)
    
        ax8 = plt.subplot(5,3,14)
        plt.title('Phi = 2 - 20',fontsize=14)
        plt.xlim(2,20)
        plt.ylim(0,1)
        plt.grid(True)
        sns.scatterplot(x='Phi min',y='Score',data=data,marker=markers[ii],facecolors='none'*(markers[ii] not in emptymarkers)+colors[ii]*(markers[ii] in emptymarkers),edgecolors='none'*(markers[ii] in emptymarkers)+colors[ii]*(markers[ii] not in emptymarkers),)
        tick_positions = np.linspace(2, 20, 7)
        plt.xticks(tick_positions)
    
        ax9 = plt.subplot(5,3,15)
        plt.title('Phi = 100 (pyrolysis)',fontsize=14)
        plt.xlim(99,101)
        plt.ylim(0,1)
        plt.grid(True)
        sns.scatterplot(x='Phi min',y='Score',data=data,marker=markers[ii],facecolors='none'*(markers[ii] not in emptymarkers)+colors[ii]*(markers[ii] in emptymarkers),edgecolors='none'*(markers[ii] in emptymarkers)+colors[ii]*(markers[ii] not in emptymarkers),)
        tick_positions = np.linspace(99, 101, 3)
        plt.xticks(tick_positions)

        axes = [ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8, ax9]
        ax1.set(xlabel=None)
        ax2.set(xlabel=None)
        ax3.set(xlabel=None)
        ax4.set(xlabel=None)
        ax5.set(xlabel=None)
        ax5.set(ylabel=None)
        ax6.set(xlabel=None)
        ax6.set(ylabel=None)
        ax7.set(xlabel=None)
        ax8.set(xlabel=None)
        ax8.set(ylabel=None)
        ax9.set(xlabel=None)
        ax9.set(ylabel=None)

        ax5.set_yticklabels([])
        ax6.set_yticklabels([])
        ax8.set_yticklabels([])
        ax9.set_yticklabels([])


    #plt.show()

    #plots hystograms for the worst quartile of a fuels
    if plots_quartili == True:
        w = 0.5
        data = data.sort_values(by = 'Score')
        q1 = int(data.shape[0]/4)
        dataq1 = data.iloc[:q1]
        dataq1['Target'] = dataq1['Target'].str.replace('_x','')
        IDSq1 = dataq1["Exp SciExpeM ID"].unique()

        print(sorted(IDSq1))

        plt.figure(figsize=(32*cm, 18*cm),tight_layout=True)

        ax1 = plt.subplot(5,1,1)
        plt.title('Target',fontsize=14)
        #plt.ylim(0,1)
        string_counts = Counter(dataq1['Target']) # Extract the strings and their corresponding counts
        strings = list(string_counts.keys())
        counts = list(string_counts.values()) # Create a bar chart
        ax1.bar(dataq1['Target'].unique(),counts, width=w)#, bins = bins_Tmin)
        ax1.grid(True, linestyle='--', alpha=0.5)
        if len(counts) > targets_length:
            plt.xticks(fontsize=fontsize)

        ax2 = plt.subplot(5,1,2)
        plt.title('T min',fontsize=14)
        #plt.ylim(0,1)
        bin_edges = np.linspace(Tminn, Tminn + NNN*deltaT_interval, NNN+1)
        ax2.hist(dataq1['Temperature min'], bins = bin_edges)
        ax2.grid(True, linestyle='--', alpha=0.5)
        plt.xticks(bin_edges)

        ax3 = plt.subplot(5,1,3)
        plt.title('T max',fontsize=14)
        ax3.hist(dataq1['Temperature max'], bins = bin_edges)
        ax3.grid(True, linestyle='--', alpha=0.5)
        plt.xticks(bin_edges)

        ax4 = plt.subplot(5,3,10)
        bin_edges = np.linspace(0,10,11)
        plt.title('P = 0 - 10 atm',fontsize=14)
        ax4.hist(dataq1['Pressure min'], bins = bin_edges)
        ax4.grid(True, linestyle='--', alpha=0.5)

        ax5 = plt.subplot(5,3,11)
        bin_edges = np.linspace(10,100,9)
        plt.title('P = 10 - 100 atm',fontsize=14)
        ax5.hist(dataq1['Pressure min'], bins = bin_edges)
        ax5.grid(True, linestyle='--', alpha=0.5)

        ax6 = plt.subplot(5,3,12)
        bin_edges = np.linspace(100,1000,4)
        plt.title('P = 100 - 1000 atm',fontsize=14)
        ax6.hist(dataq1['Pressure min'], bins = bin_edges)
        ax6.grid(True, linestyle='--', alpha=0.5)

        ax7 = plt.subplot(5,3,13)
        bin_edges = np.linspace(0,5,11)
        plt.title('Phi = 0 - 5',fontsize=14)
        ax7.hist(dataq1['Phi min'], bins = bin_edges)
        ax7.grid(True, linestyle='--', alpha=0.5)

        ax8 = plt.subplot(5,3,14)
        bin_edges = np.linspace(5,20,4)
        plt.title('Phi = 5 - 20',fontsize=14)
        ax8.hist(dataq1['Phi min'], bins = bin_edges)
        ax8.grid(True, linestyle='--', alpha=0.5)
        plt.xticks(bin_edges)

        ax9 = plt.subplot(5,3,15)
        bin_edges = np.linspace(20,100,5)
        plt.title('Phi = 20 - 100',fontsize=14)
        ax9.hist(dataq1['Phi min'], bins = bin_edges)
        ax9.grid(True, linestyle='--', alpha=0.5)

        axes = [ax1,ax2,ax3,ax4,ax5,ax6,ax7,ax8,ax9]

        plt.show()
        print()

plt.savefig(os.path.join(path, fuel + models[1] + '.pdf'),dpi=300)
        