from artificial_dwarf import artificial_dwarf
#from artificial_dwarf_nopsf import artificial_dwarf

filename = 'empty_region.fits'
psf = 'KK98a189_psf.fits'
apparent_magnitude = 17
R_eff = 50
n = 1.2
axisratio = 1 
theta = 0
x0 = 500
y0 = 500
display = False
save = 'HIGHER_sersic'

artificial_dwarf(filename,psf,apparent_magnitude,R_eff,n,axisratio,theta,x0,y0,display,save)

filename = 'empty_region.fits'
psf = 'KK98a189_psf.fits'
apparent_magnitude = 17
R_eff = 50
n = 0.7
axisratio = 1
theta = 0
x0 = 500
y0 = 500
display = False
save = 'MIDDLE_sersic'

artificial_dwarf(filename,psf,apparent_magnitude,R_eff,n,axisratio,theta,x0,y0,display,save)

filename = 'empty_region.fits'
psf = 'KK98a189_psf.fits'
apparent_magnitude = 17
R_eff = 50
n = 0.3
axisratio = 1
theta = 0
x0 = 500
y0 = 500
display = False
save = 'LOWER_sersic'

artificial_dwarf(filename,psf,apparent_magnitude,R_eff,n,axisratio,theta,x0,y0,display,save)