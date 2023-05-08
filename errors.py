#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May  5 10:55:00 2023

@author: jryan4
"""

import numpy as np

worldgcp = [[5.00158271e+05, 8.72428273e+06, 3.31143000e+02],
 [5.00177081e+05, 8.72432397e+06, 3.19108000e+02],
 [5.00125052e+05, 8.72434826e+06, 3.32214000e+02]] 

worldgcp_proj = [[5.00154539e+05, 8.72428111e+06, 3.30791444e+02],
 [5.00174852e+05, 8.72432331e+06, 3.19387998e+02],
 [5.00098514e+05, 8.72434643e+06, 3.31742339e+02]]



#%%
# Compute Z residual error
vertical_error = (np.abs((worldgcp_proj[0][2] - worldgcp[0][2]))+\
                 (np.abs(worldgcp_proj[1][2] - worldgcp[1][2]))+\
                 (np.abs(worldgcp_proj[2][2] - worldgcp[2][2]))) / 3

    
print(f'Z residual: {vertical_error} metres')
    
# Compute XY residual error for "good GCPS"
residual_xy=[]
for i in (0,1):
    residual_xy.append(np.sqrt((worldgcp_proj[i][0]-worldgcp[i][0])**2 +
                            (worldgcp_proj[i][1]-worldgcp[i][1])**2))  
residual_xy = np.nanmean(np.array(residual_xy))

print(f'Good XY residual: {residual_xy} metres')


residual_bad = np.sqrt((worldgcp_proj[2][0]-worldgcp[2][0])**2 +\
                       (worldgcp_proj[2][1]-worldgcp[2][1])**2)  


print(f'Bad XY residual: {residual_bad} metres')





