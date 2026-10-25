# Exploratory error analysis (POST-HOC, NOT pre-registered)

Tune+validation only; locked untouched; pre-registered results unchanged.

MAE 1.216, RMSE 2.006, n=7194

| group | n | MAE | RMSE |
|---|---|---|---|
| MW>500 | 205 | 2.513 | 3.494 |
| charged | 450 | 1.067 | 1.365 |
| metal-containing | 60 | 3.868 | 4.554 |
| multi-component | 761 | 2.909 | 4.560 |
| neutral single-component <=500 | 5718 | 0.928 | 1.222 |

## Top 20 worst predictions (P-A)

| name | smiles | measured | predicted | error |
|---|---|---|---|---|
| 1,3-dimethyl-5-propylbenzene; 6,6,22,22-tetrabutyloctapentacontane; anthracene; phenylbenzene; tetraheptacontane | CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC.CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC(CCCC)(CCCC)CCCCCCCCCCCCCCCC(CCCC)(CCCC)CCCCC.CCCc1cc(C)cc(C)c1.c2ccc(cc2)c3ccccc3.c4ccc5cc6ccccc6cc5c4 | -6.81 | -49.72 | -42.91 |
| 1,3-xylene; 1,4-diethylcyclohexane; 8,15-diethylhexacosane; anthracene; naphthalene; tetradecahydroanthracene; triacontane | CCCCCCCCCCCCCCCCCCCCCCCCCCCCCC.CCCCCCCCCCCC(CC)CCCCCCC(CC)CCCCCCC.CCC1CCC(CC)CC1.Cc2cccc(C)c2.C3CCC4CC5CCCCC5CC4C3.c6ccc7ccccc7c6.c8ccc9cc%10ccccc%10cc9c8 | -5.41 | -32.00 | -26.60 |
| (2-phenylbutan-2-yl)benzene; (2-phenylethyl)benzene; 1,2,4,5-tetraethylbenzene; 1-methyl-2-phenylbenzene; 1-methylnaphthalene; benzene; cyclohexylbenzene; ethenylbenzene; ethylbenzene; phenylbenzene; toluene | CCc1ccccc1.CCc2cc(CC)c(CC)cc2CC.CCC(C)(c3ccccc3)c4ccccc4.Cc5ccccc5.Cc6ccccc6c7ccccc7.Cc8cccc9ccccc89.C=Cc%10ccccc%10.C%11CCC(CC%11)c%12ccccc%12.C(Cc%13ccccc%13)c%14ccccc%14.c%15ccccc%15.c%16ccc(cc%16)c%17ccccc%17 | -4.59 | -30.67 | -26.09 |
| disodium bis[(oxoboranyl)oxy]bicyclo[5.5.1]hexaboroxane-3,5-bis(olate) | O.O.O.O.[Na+].[Na+].[O-]B([O-])[O-].[O-]B([O-])[O-].[O-]B([O-])[O-].[O-]B([O-])[O-].[O-]B([O-])[O-].[O-]B([O-])[O-].[O-]B([O-])[O-].[O-]B([O-])[O-] | -0.42 | 22.26 | +22.68 |
| dialuminium tris[2-(2,4,5,7-tetrabromo-6-oxido-3-oxoxanthen-9-yl)-3,4,5,6-tetrachlorobenzoate] | [Al+3].[Al+3].[O-]C(=O)c1c(Cl)c(Cl)c(Cl)c(Cl)c1C2=C3C=C(Br)C(=O)C(=C3Oc4c(Br)c([O-])c(Br)cc24)Br.[O-]C(=O)c5c(Cl)c(Cl)c(Cl)c(Cl)c5C6=C7C=C(Br)C(=O)C(=C7Oc8c(Br)c([O-])c(Br)cc68)Br.[O-]C(=O)c9c(Cl)c(Cl)c(Cl)c(Cl)c9C%10=C%11C=C(Br)C(=O)C(=C%11Oc%12c(Br)c([O-])c(Br)cc%10%12)Br | -6.49 | -28.80 | -22.31 |
| 3,3,4,4,5,5,6,6,7,7,8,8,8-tridecafluorooctyl prop-2-enoate 3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,10-heptadecafluorodecyl prop-2-enoate 3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,12-henicosafluorododecyl prop-2-enoate 3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13,14,14,14-pentacosafluorotetradecyl prop-2-enoate | FC(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)CCOC(=O)C=C.FC(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)CCOC(=O)C=C.FC(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)CCOC(=O)C=C.FC(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)CCOC(=O)C=C | -6.48 | -28.04 | -21.56 |
| N,N',N'',N'''-tetrakis(4,6-bis(butyl-(N-methyl-2,2,6,6-tetramethylpiperidin-4-yl)amino)triazin-2-yl)-4,7-diazadecane-1,10-diamine | CCCCN(C1CC(C)(C)N(C)C(C)(C)C1)c2nc(NCCCN(CCN(CCCNc3nc(nc(n3)N(CCCC)C4CC(C)(C)N(C)C(C)(C)C4)N(CCCC)C5CC(C)(C)N(C)C(C)(C)C5)c6nc(nc(n6)N(CCCC)C7CC(C)(C)N(C)C(C)(C)C7)N(CCCC)C8CC(C)(C)N(C)C(C)(C)C8)c9nc(nc(n9)N(CCCC)C%10CC(C)(C)N(C)C(C)(C)C%10)N(CCCC)C%11CC(C)(C)N(C)C(C)(C)C%11)nc(n2)N(CCCC)C%12CC(C)(C)N(C)C(C)(C)C%12 | -5.36 | -26.75 | -21.39 |
| 2-[(E)-2-(2-chloro-4-{3-chloro-4-[(E)-2-{1-[(2,4-dimethylphenyl)carbamoyl]-2-oxopropyl}diazen-1-yl]phenyl}phenyl)diazen-1-yl]-N-(2,4-dimethylphenyl)-3-oxobutanamide; N-(4-chloro-2,5-dimethoxyphenyl)-2-[(E)-2-(2-chloro-4-{3-chloro-4-[(E)-2-{1-[(2,4-dimethylphenyl)carbamoyl]-2-oxopropyl}diazen-1-yl]phenyl}phenyl)diazen-1-yl]-3-oxobutanamide; N-(4-chloro-2,5-dimethoxyphenyl)-2-[(E)-2-(2-chloro-4-{3-chloro-4-[(E)-2-{1-[(4-chloro-2,5-dimethoxyphenyl)carbamoyl]-2-oxopropyl}diazen-1-yl]phenyl}phenyl)diazen-1-yl]-3-oxobutanamide | COc1cc(NC(=O)C(N=Nc2ccc(cc2Cl)c3ccc(N=NC(C(C)=O)C(=O)Nc4ccc(C)cc4C)c(Cl)c3)C(C)=O)c(OC)cc1Cl.COc5cc(NC(=O)C(N=Nc6ccc(cc6Cl)c7ccc(N=NC(C(C)=O)C(=O)Nc8cc(OC)c(Cl)cc8OC)c(Cl)c7)C(C)=O)c(OC)cc5Cl.CC(=O)C(N=Nc9ccc(cc9Cl)c%10ccc(N=NC(C(C)=O)C(=O)Nc%11ccc(C)cc%11C)c(Cl)c%10)C(=O)Nc%12ccc(C)cc%12C | -9.05 | -29.19 | -20.14 |
| {2-hydroxy-3-[(9Z)-octadec-9-enoyloxy]propoxy}boronic acid 2-hydroxy-3-{[hydroxy({2-hydroxy-3-[(9Z)-octadec-9-enoyloxy]propoxy})boranyl]oxy}propyl (9Z)-octadec-9-enoate 3-{[bis({2-hydroxy-3-[(9Z)-octadec-9-enoyloxy]propoxy})boranyl]oxy}-2-hydroxypropyl (9Z)-octadec-9-enoate | CCCCCCCC\C=C/CCCCCCCC(=O)OCC(O)COB(O)O.CCCCCCCC\C=C/CCCCCCCC(=O)OCC(O)COB(O)OCC(O)COC(=O)CCCCCCC\C=C/CCCCCCCC.CCCCCCCC\C=C/CCCCCCCC(=O)OCC(O)COB(OCC(O)COC(=O)CCCCCCC\C=C/CCCCCCCC)OCC(O)COC(=O)CCCCCCC\C=C/CCCCCCCC | -5.35 | -24.34 | -18.99 |
| trisodium hexafluoroalumanetriuide | [F-].[F-].[F-].[F-].[F-].[F-].[Na+].[Na+].[Na+].[Al+3] | -2.70 | 16.09 | +18.78 |
| trilithium(1+) ion hexafluoroalumanetriuide | [Li+].[Li+].[Li+].[F-].[F-].[F-].[F-].[F-].[F-].[Al+3] | -2.17 | 16.38 | +18.55 |
| 1,2,3,4-tetrahydronaphthalene; 1,3,5-trimethylbenzene; 1,4-diethylbenzene; 1H-indene; 2,3-dihydro-1H-indene; benzene; naphthalene; propan-2-ylbenzene; toluene | CCc1ccc(CC)cc1.CC(C)c2ccccc2.Cc3ccccc3.Cc4cc(C)cc(C)c4.C5CCc6ccccc6C5.C7Cc8ccccc8C7.C9C=Cc%10ccccc9%10.c%11ccccc%11.c%12ccc%13ccccc%13c%12 | -3.54 | -20.33 | -16.79 |
| pentasodium 2-[bis({2-[bis(carboxylatomethyl)amino]ethyl})amino]acetate | [Na+].[Na+].[Na+].[Na+].[Na+].[O-]C(=O)CN(CCN(CC([O-])=O)CC([O-])=O)CCN(CC([O-])=O)CC([O-])=O | 0.20 | 13.43 | +13.23 |
| dialuminium(3+) ion trisulfate | O.O.O.O.O.O.O.O.O.[Al+3].[Al+3].[O-][S]([O-])(=O)=O.[O-][S]([O-])(=O)=O.[O-][S]([O-])(=O)=O | -7.50 | 4.72 | +12.22 |
| cobalt(3+) ion 9-(2-carboxyphenyl)-6-(diethylamino)-N,N-diethyl-3H-xanthen-3-iminium bis(3-methyl-4-[(E)-2-(2-oxido-5-{[3-(propan-2-yloxy)propyl]sulfamoyl}phenyl)diazen-1-yl]-1-phenyl-1H-pyrazol-5-olate) | [Co+3].CCN(CC)c1ccc2c(c1)[o+]c3cc(ccc3c2c4ccccc4C(O)=O)N(CC)CC.CC(C)OCCCN[S](=O)(=O)c5ccc([O-])c(c5)N=Nc6c(C)nn(c6[O-])c7ccccc7.CC(C)OCCCN[S](=O)(=O)c8ccc([O-])c(c8)N=Nc9c(C)nn(c9[O-])c%10ccccc%10 | -3.24 | -15.29 | -12.05 |
| 2,6-diethylanthracene; 9,9-dipropylicosane; tricosane | CCCCCCCCCCCCCCCCCCCCCCC.CCCCCCCCCCCC(CCC)(CCC)CCCCCCCC.CCc1ccc2cc3cc(CC)ccc3cc2c1 | -6.36 | -18.38 | -12.02 |
| aluminium(3+) ion dichloride hydroxide | [Al+3].[Cl-].[Cl-].[Cl-] | -6.57 | 5.24 | +11.80 |
| Talc (Mg3H2(SiO3)4) | [Mg++].[Mg++].[Mg++].O[Si]([O-])=O.O[Si]([O-])=O.[O-][Si]([O-])=O.[O-][Si]([O-])=O | -6.58 | 4.98 | +11.56 |
| N-[2-(2-heptadecyl-4,5-dihydro-1H-imidazol-1-yl)ethyl]octadecanamide; N-{2-[(2-octadecanamidoethyl)amino]ethyl}octadecanamide; bis(acetic acid) | CCCCCCCCCCCCCCCCCC(=O)NCCNCCNC(=O)CCCCCCCCCCCCCCCCC.CCCCCCCCCCCCCCCCCC(=O)NCCN1CCN=C1CCCCCCCCCCCCCCCCC.CC(O)=O.CC(O)=O | -7.14 | -18.57 | -11.43 |
| aluminium(3+) ion magnesium(2+) ion sodium tris(oxosilanebis(olate)) | [Na+].[Mg++].[Al+3].[O-][Si]([O-])=O.[O-][Si]([O-])=O.[O-][Si]([O-])=O | -5.13 | 6.09 | +11.22 |
