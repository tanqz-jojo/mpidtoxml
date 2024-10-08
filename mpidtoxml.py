from __future__ import print_function
import sys
import math
import copy
from simtk.unit import *
import numpy as np

section = None
atomTypes = []
atomClasses = {}
residue = None
residues = []
patches = {}
category = None
bonds = []
angles = []
ubs = []
dihedrals = {}
impropers = []
cmaps = []
cmap = None
nonbondeds = {}
nbfixes = {}
mutipoles = {}
polarize = {}


bohr = 0.52917720859
dCon = 0.1*bohr
qCon = 0.01*bohr*bohr/3.0
oCon = 0.001*bohr*bohr*bohr/15.0
sf = 3*[dCon]+6*[qCon]+10*[oCon]

def getFieldPairs(fields):
    pairs = []
    for i in range(len(fields)//2):
        pairs.append((fields[2*i], fields[2*i+1]))
    return pairs

class Residue(object):
    def __init__(self, name):
        self.name = name
        self.atoms = []
        self.atomMap = {}
        self.deletions = []
        self.bonds = []
        self.externalBonds = ['N', 'C']
        otherresidue = ['ALA','ARG','ASN', 'ASP', 'CYS', 'GLN', 'GLU', 'HSD', 'HSE', 'HSP', 'ILE', 'LEU', 'LYS', 'NLE', 'MET', 'PHE', 'SER', 'THR', 'TRP', 'TYR', 'VAL']
        if name == 'GLY':
            self.patches = ['NTER', 'CTEG']
        elif name == 'PRO':
            self.patches = ['NTER', 'CTEP']
        elif name in otherresidue:
            self.patches = ['NTER', 'CTER']
        else:
            self.patches = ['NONE', 'NONE']
        self.lonepairs = []
    
    def addAtom(self, atom):
        self.atomMap[atom.name] = len(self.atoms)
        self.atoms.append(atom)
    
    def setAtomAnisotropy(self, fields):
        atom1 = [a for a in self.atoms if a.name == fields[1]][0]
        atom2 = [a for a in self.atoms if a.name == fields[2]][0]
        atom3 = [a for a in self.atoms if a.name == fields[3]][0]
        atom4 = [a for a in self.atoms if a.name == fields[4]][0]
        for param, value in getFieldPairs(fields[5:]):
            if param == 'A11':
                a11 = float(value)
            elif param == 'A22':
                a22 = float(value)
        atom1.anisotropic = True
        atom1.anisotropy = (atom2.type, atom3.type, atom4.type, a11, a22)
     
    def setAtomMultipole(self, fields):
        mpole_atom = [a for a in self.atoms if a.name == fields[1]][0]    
        kz_atom = [a for a in self.atoms if a.name == fields[4]][0]
        #print(fields[5][0])    
        #print(fields[5])    
        kx_atom = [a for a in self.atoms if a.name == fields[5]][0]    
        axisInfo = fields[2]
        multipole_vals = [float(fields[6]), float(fields[7]), float(fields[8]), float(fields[9]), float(fields[10]), float(fields[11]), float(fields[12]), float(fields[13]), float(fields[14]), float(fields[15]), float(fields[16]), float(fields[17]), float(fields[18]), float(fields[19]), float(fields[20]), float(fields[21]), float(fields[22]), float(fields[23]), float(fields[24])] 
        multipole = np.multiply(sf, multipole_vals)
        mpole_atom.mpole = True
        if axisInfo == "BISECT":
           mpole_atom.multipoles = [mpole_atom.type, kz_atom.type, -kx_atom.type, axisInfo, multipole[0], multipole[1], multipole[2], multipole[3], multipole[4], multipole[5], multipole[6], multipole[7], multipole[8], multipole[9], multipole[10], multipole[11], multipole[12], multipole[13], multipole[14], multipole[15], multipole[16], multipole[17], multipole[18]]
        else:
           mpole_atom.multipoles = [mpole_atom.type, kz_atom.type, kx_atom.type, axisInfo, multipole[0], multipole[1], multipole[2], multipole[3], multipole[4], multipole[5], multipole[6], multipole[7], multipole[8], multipole[9], multipole[10], multipole[11], multipole[12], multipole[13], multipole[14], multipole[15], multipole[16], multipole[17], multipole[18]]

    def setAtomPolarize(self, fields):
        polar_atom = [a for a in self.atoms if a.name == fields[1]][0]
        polarizability = float(fields[2]) * 0.001
        thole = float(fields[3])
        axisInfo = 'Isotropic'
        polar_atom.polarize = [polar_atom.type, axisInfo, polarizability, polarizability, polarizability, thole]
        polar_atom.multipoles = [polar_atom.type, -1, -1, axisInfo, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    
    def setAtomApolarize(self, fields):
        polar_atom = [a for a in self.atoms if a.name == fields[1]][0]
        polarizabilityXX = float(fields[6]) * 0.001    
        polarizabilityYY = float(fields[7]) * 0.001    
        polarizabilityZZ = float(fields[8]) * 0.001
        thole = float(fields[9])
        axisInfo = fields[2]
        polar_atom.polarize = [polar_atom.type, axisInfo, polarizabilityXX, polarizabilityYY, polarizabilityZZ, thole]     

def createPatchedResidue(residue, patch):
    r = Residue(patch.name+'-'+residue.name)
    for atom in patch.atoms:
        r.addAtom(atom)
    atomNames = set(atom.name for atom in r.atoms)
    for atom in residue.atoms:
        if atom.name not in patch.deletions:
            if atom.name not in atomNames:
                r.addAtom(atom)
                atomNames.add(atom.name)
            else:
                # We're using the version from the patch, but we still need to take anisotropy information from the original residue.
                for i in range(len(r.atoms)):
                    if r.atoms[i].name == atom.name:
                        newAtom = copy.deepcopy(r.atoms[i])
                        newAtom.anisotropic = atom.anisotropic
                        if atom.anisotropic:
                            name2 = [a for a in residue.atoms if a.type == atom.anisotropy[0]][0].name
                            name3 = [a for a in residue.atoms if a.type == atom.anisotropy[1]][0].name
                            name4 = [a for a in residue.atoms if a.type == atom.anisotropy[2]][0].name
                            atom2 = [a for a in r.atoms if a.name == name2][0]
                            atom3 = [a for a in r.atoms if a.name == name3][0]
                            atom4 = [a for a in r.atoms if a.name == name4][0]
                            newAtom.anisotropy = (atom2.type, atom3.type, atom4.type, atom.anisotropy[3], atom.anisotropy[4])
                        r.atoms[i] = newAtom
    for bond in residue.bonds:
        if all(atom in atomNames for atom in bond):
            r.bonds.append(bond)
    for bond in patch.bonds:
        r.bonds.append(bond)
    for lp in residue.lonepairs:
        if all(atom in atomNames for atom in lp[:4]):
            r.lonepairs.append(lp)
    for lp in patch.lonepairs:
        r.lonepairs.append(lp)
    return r

class Atom(object):
    def __init__(self, fields):
        self.name = fields[1]
        self.atomClass = fields[2]
        self.charge = float(fields[3])
        self.polarizable = False
        self.anisotropic = False
        self.mpole = False
        for param, value in getFieldPairs(fields[4:]):
            if param == 'ALPHA':
                self.polarizable = True
                self.alpha = float(value)*angstrom**3/(138.935456*kilojoules_per_mole*nanometer)
            elif param == 'THOLE':
                self.thole = float(value)
            elif param == 'TYPE':
                self.drudeType = value
        if 'drudeType' not in dir(self):
            self.drudeType = 'DRUD'
        if self.polarizable:
            sign = 1
            if self.alpha < 0*nanometers**2/kilojoules_per_mole:
                self.alpha = -self.alpha
                sign = -1
            self.drudeCharge = sign*math.sqrt(self.alpha*2*(500*kilocalories_per_mole/angstrom**2))
            self.charge -= self.drudeCharge
            if 'thole' not in dir(self):
                self.thole = 1.3
        #if self.mpole == False:
        #   self.multipoles=[self.type, ' ', ' ', ' ', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.type = len(atomTypes)
        atomTypes.append(self)
        if self.mpole == False:
           self.multipoles=[self.type, -1, -1, ' ', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
           self.polarize = [self.type, ' ', 0.0, 0.0, 0.0, 0.0]

class Cmap(object):
    def __init__(self, fields):
        if fields[1] != fields[4] or fields[2] != fields[5] or fields[3] != fields[6]:
            raise ValueError('Invalid CMAP atoms: '+(' '.join(fields[:8])))
        self.classes = [fields[0], fields[1], fields[2], fields[3], fields[7]]
        self.size = int(fields[8])
        self.values = []

class Nonbonded(object):
    def __init__(self, fields):
        self.atomClass = fields[0]
        values = [float(x) for x in fields[1:]]
        if values[1] > 0 or (len(values) > 3 and values[4] > 0):
            raise ValueError('Unsupported nonbonded type')
        self.epsilon = -values[1]*kilocalories_per_mole
        self.sigma = values[2]*angstroms
        if len(values) > 3:
            self.epsilon14 = -values[4]*kilocalories_per_mole
            self.sigma14 = values[5]*angstroms
        else:
            #self.epsilon14 = self.epsilon
            self.epsilon14 = 0.0*kilocalories_per_mole
            #self.sigma14 = self.sigma
            self.sigma14 = 0.0*angstroms

def getLennardJonesParams(class1, class2, is14):
    nbfixParams = None
    if (class1, class2) in nbfixes:
        nbfixParams = nbfixes[(class1, class2)]
    elif (class2, class1) in nbfixes:
        nbfixParams = nbfixes[(class2, class1)]
    if nbfixParams is not None:
        if is14 and len(nbfixParams) > 2:
            return nbfixParams[2:3]
        return nbfixParams
    if class1 not in nonbondeds or class2 not in nonbondeds: # Probably a Drude particle
        return (0*kilojoules_per_mole, 1*nanometers)
    params1 = nonbondeds[class1]
    params2 = nonbondeds[class2]
    if is14:
        return (sqrt(params1.epsilon14*params2.epsilon14), params1.sigma14+params2.sigma14)
    return (sqrt(params1.epsilon*params2.epsilon), params1.sigma+params2.sigma)


continuedLine = None
for inputfile in sys.argv[1:]:
    for line in open(inputfile):
        if continuedLine is not None:
            line = continuedLine+' '+line
            continuedLine = None
        if line.find('!') > -1:
            line = line[:line.find('!')]
        line = line.strip()
        if line.endswith('-'):
            continuedLine = line[:-1]
            continue
        fields = line.split()
        if len(fields) == 0:
            continue
        if line == 'read rtf card':
            section = 'rtf'
        elif line == 'read para card':
            section = 'para'
        elif line == 'end':
            section = None
        elif section == 'rtf':
            if fields[0] == 'MASS':
                atomClasses[fields[2]] = (float(fields[3]), fields[4])
            elif fields[0] == 'RESI':
                residue = Residue(fields[1])
                residues.append(residue)
            elif fields[0] == 'PRES':
                residue = Residue(fields[1])
                patches[residue.name] = residue
            elif fields[0] == 'ATOM':
                residue.addAtom(Atom(fields))
            elif fields[0].startswith('DELE') and fields[1] == 'ATOM':
                residue.deletions.append(fields[2])
            elif fields[0] == 'BOND':
                for name1, name2 in getFieldPairs(fields[1:]):
                    residue.bonds.append((name1, name2))
            elif fields[0].startswith('PATC'):
                for pos, name in getFieldPairs(fields[1:]):
                    if pos.startswith('FIRS'):
                        residue.patches[0] = name
                    elif pos == 'LAST':
                        residue.patches[1] = name
            elif fields[0] == 'ANISOTROPY':
                residue.setAtomAnisotropy(fields)
            elif fields[0] == 'LONEPAIR':
                params = dict(getFieldPairs(fields[6:]))
                residue.lonepairs.append(fields[2:6]+[fields[1], float(params['distance'])*angstrom, float(params['angle'])*degrees, float(params['dihe'])*degrees])
            elif fields[0] == 'OPOLE':
                residue.setAtomMultipole(fields) 
            elif fields[0] == 'POLARIZE':
                residue.setAtomPolarize(fields)
            elif fields[0] == 'APOLARIZE':
                residue.setAtomApolarize(fields)

        elif section == 'para':
            if fields[0] in ('BONDS', 'ANGLES', 'DIHEDRALS', 'IMPROPER', 'CMAP','NONBONDED', 'NBFIX', 'THOLE'):
                category = fields[0]
                residue = None
            elif category == 'BONDS':
                bonds.append((fields[0], fields[1], 2*float(fields[2])*kilocalories_per_mole/angstrom**2, float(fields[3])*angstroms))
            elif category == 'ANGLES':
                #if len(fields) == 5:
                angles.append((fields[0], fields[1], fields[2], 2*float(fields[3])*kilocalories_per_mole/radian**2, float(fields[4])*degrees))
                #else:
                if len(fields) > 5:
                    ubs.append((fields[0], fields[1], fields[2], 2*float(fields[3])*kilocalories_per_mole/radian**2, float(fields[4])*degrees, 2*float(fields[5])*kilocalories_per_mole/angstrom**2, float(fields[6])*angstroms))
            elif category == 'DIHEDRALS':
                key = (fields[0], fields[1], fields[2], fields[3])
                if key not in dihedrals:
                    dihedrals[key] = []
                dihedrals[key].append((float(fields[4])*kilocalories_per_mole, int(fields[5]), float(fields[6])*degrees))
            elif category == 'IMPROPER':
                impropers.append((fields[0], fields[1], fields[2], fields[3], float(fields[4])*kilocalories_per_mole/radian**2, float(fields[6])*degrees))
            elif category == 'CMAP':
                if cmap is None:
                    cmap = Cmap(fields)
                    cmaps.append(cmap)
                else:
                    cmap.values += [float(x) for x in fields]
                    if len(cmap.values) > cmap.size*cmap.size:
                        raise ValueError('Too many values for CMAP')
                    if len(cmap.values) == cmap.size*cmap.size:
                        cmap = None
            elif category == 'NONBONDED':
                nb = Nonbonded(fields)
                nonbondeds[nb.atomClass] = nb
            elif category == 'NBFIX':
                nbfixes[(fields[0], fields[1])] = [fields[0], fields[1], -float(fields[2])*kilocalories_per_mole, float(fields[3])*angstroms]
                #nbfixes[fields[0]] = [fields[1], -float(fields[2])*kilocalories_per_mole, float(fields[3])*angstroms]

# Apply patches to create terminal residues.

patchedResidues = []
for residue in residues:
    patchedResidues.append(residue)
    if residue.patches[0] in patches:
        patched = createPatchedResidue(residue, patches[residue.patches[0]])
        patched.externalBonds[0] = ''
        patchedResidues.append(patched)
    if residue.patches[1] in patches:
        patched = createPatchedResidue(residue, patches[residue.patches[1]])
        patched.externalBonds[1] = ''
        patchedResidues.append(patched)
residues = patchedResidues

# Build a list of all unique maps used in CMAP terms.

uniqueCmaps = {}
for cmap in cmaps:
    cmap.values = tuple(cmap.values)
    if cmap.values not in uniqueCmaps:
        uniqueCmaps[cmap.values] = len(uniqueCmaps)

# Create Drude particles.

drudes = {}
for residue in residues:
    atoms2 = residue.atoms[:]
    for atom in residue.atoms:
        if atom.polarizable:
            drude = Atom(('', 'D'+atom.name, atom.drudeType, atom.drudeCharge))
            atoms2.append(drude)
            if atom.anisotropic:
                aniso = atom.anisotropy
            else:
                aniso = None
            drudes[(drude.type, atom.type)] = (138.935456*atom.alpha.value_in_unit(nanometers**2/kilojoules_per_mole), atom.thole, atom.drudeCharge, aniso)
    residue.atoms = atoms2

# Create the XML file.

print('<ForceField>')
print(' <AtomTypes>')
masslessTypes = set()
for type in atomTypes:
    (mass, elem) = atomClasses[type.atomClass]
    if mass == 0.0:
        elementSpec = ''
        masslessTypes.add(type.type)
    else:
        elementSpec = ' element="%s"' % elem
    print('  <Type name="%d" class="%s"%s mass="%f"/>' % (type.type, type.atomClass, elementSpec, mass))
print(' </AtomTypes>')
print(' <Residues>')
for residue in residues:
    print('  <Residue name="%s">' % residue.name)
    masslessAtoms = set()
    for atom in residue.atoms:
        print('   <Atom name="%s" type="%d"/>' % (atom.name, atom.type))
        if atom.type in masslessTypes:
            masslessAtoms.add(atom.name)
    for name1, name2 in residue.bonds:
        if name1 in residue.atomMap and name2 in residue.atomMap:
            if name1 not in masslessAtoms and name2 not in masslessAtoms: # CHARMM lists bonds for lone pairs, which we don't want
                print('   <Bond from="%d" to="%d"/>' % (residue.atomMap[name1], residue.atomMap[name2]))
    for external in residue.externalBonds:
        if external in residue.atomMap:
            print('   <ExternalBond from="%d"/>' % residue.atomMap[external])
    for lp in residue.lonepairs:
        atoms = [residue.atomMap[lp[0]], residue.atomMap[lp[1]], residue.atomMap[lp[3]], residue.atomMap[lp[2]], residue.atomMap[lp[1]]]
        if lp[4] == 'relative':
            xweights = [-1.0, 0.0, 1.0]
        elif lp[4] == 'bisector':
            xweights = [-1.0, 0.5, 0.5]
        else:
            raise ValueError('Unknown lonepair type: '+lp[4])
        r = lp[5].value_in_unit(nanometer)
        theta = lp[6].value_in_unit(radian)
        phi = (180*degrees-lp[7]).value_in_unit(radian)
        p = [r*math.cos(theta), r*math.sin(theta)*math.cos(phi), r*math.sin(theta)*math.sin(phi)]
        p = [x if abs(x) > 1e-10 else 0 for x in p] # Avoid tiny numbers caused by roundoff error
        print('   <VirtualSite type="localCoords" index="%d" atom1="%d" atom2="%d" atom3="%d" excludeWith="%d" wo1="1" wo2="0" wo3="0" wx1="%g" wx2="%g" wx3="%g" wy1="0" wy2="-1" wy3="1" p1="%g" p2="%g" p3="%g"/>' % tuple(atoms+xweights+p))
    print('  </Residue>')
print(' </Residues>')
print(' <HarmonicBondForce>')
for bond in bonds:
    print('  <Bond class1="%s" class2="%s" length="%g" k="%.12g"/>' % (bond[0], bond[1], bond[3].value_in_unit(nanometer), bond[2].value_in_unit(kilojoules_per_mole/nanometer**2)))
    #print('  <Bond class1="%s" class2="%s" length="%g" k="%.12g"/>' % (bond[0], bond[1], bond[3].value_in_unit(nanometer), 0.0))
print(' </HarmonicBondForce>')
print(' <HarmonicAngleForce>')
for angle in angles:
    print('  <Angle class1="%s" class2="%s" class3="%s" angle="%.12g" k="%.12g"/>' % (angle[0], angle[1], angle[2], angle[4].value_in_unit(radian), angle[3].value_in_unit(kilojoules_per_mole/radian**2)))
    #print('  <Angle class1="%s" class2="%s" class3="%s" angle="%.12g" k="%.12g"/>' % (angle[0], angle[1], angle[2], angle[4].value_in_unit(radian), 0.0))
print(' </HarmonicAngleForce>')
print(' <AmoebaUreyBradleyForce>')
for angle in ubs:
    print('  <UreyBradley class1="%s" class2="%s" class3="%s" d="%.12g" k="%.12g"/>' % (angle[0], angle[1], angle[2], angle[6].value_in_unit(nanometer), 0.5*angle[5].value_in_unit(kilojoules_per_mole/nanometer**2)))
    #print('  <UreyBradley class1="%s" class2="%s" class3="%s" d="%.12g" k="%.12g"/>' % (angle[0], angle[1], angle[2], angle[6].value_in_unit(nanometer), 0.0))
print(' </AmoebaUreyBradleyForce>')
print(' <PeriodicTorsionForce>')
for dihedral in dihedrals:
    values = dihedrals[dihedral]
    params = ''
    for (i, (k, n, phase)) in enumerate(values):
        params += ' periodicity%d="%d" phase%d="%.12g" k%d="%.12g"' % (i+1, n, i+1, phase.value_in_unit(radians), i+1, k.value_in_unit(kilojoules_per_mole))
        #params += ' periodicity%d="%d" phase%d="%.12g" k%d="%.12g"' % (i+1, n, i+1, phase.value_in_unit(radians), i+1, 0.0)
    print('  <Proper class1="%s" class2="%s" class3="%s" class4="%s"%s/>' % (dihedral[0], dihedral[1], dihedral[2], dihedral[3], params))
print(' </PeriodicTorsionForce>')
print(' <CustomTorsionForce energy="k*(theta-theta0)^2">')
print('  <PerTorsionParameter name="k"/>')
print('  <PerTorsionParameter name="theta0"/>')
for improper in impropers:
    print('  <Improper class1="%s" class2="%s" class3="%s" class4="%s" k="%.12g" theta0="%.12g"/>' % (improper[0], improper[1], improper[2], improper[3], improper[4].value_in_unit(kilojoules_per_mole/radian**2), improper[5].value_in_unit(radian)))
print(' </CustomTorsionForce>')
print(' <CMAPTorsionForce>')
for values in sorted(uniqueCmaps, key=lambda x: uniqueCmaps[x]):
    print('  <Map>')
    size = int(math.sqrt(len(values)))
    shift = size//2
    scale = kilocalories_per_mole.conversion_factor_to(kilojoules_per_mole)
   # Convert the ordering from the one used by CHARMM to the one used by OpenMM.
    reordered = [0]*len(values)
    for i in range(size):
        i2 = (i+shift)%size
        for j in range(size):
            j2 = (j+shift)%size
            reordered[j2*size+i2] = scale*values[i*size+j]
    for i in range(size):
        v = reordered[i*size:(i+1)*size]
        print('   '+(' '.join('%g' % x for x in v)))
    print('  </Map>')
for map in cmaps:
    print('   <Torsion map="%d" class1="%s" class2="%s" class3="%s" class4="%s" class5="%s"/>' % (uniqueCmaps[map.values], map.classes[0], map.classes[1], map.classes[2], map.classes[3], map.classes[4]))
print(' </CMAPTorsionForce>')
##print(' <NonbondedForce coulomb14scale="0.833333" lj14scale="1.0" >')
print(' <LennardJonesForce lj14scale="1.0">')
for type in nonbondeds:
    if nonbondeds[type].sigma14.value_in_unit(nanometer) == 0 and nonbondeds[type].epsilon14.value_in_unit(kilojoules_per_mole) ==0 :
       print('  <Atom class="%s" sigma="%.12g" epsilon="%.12g" />' % (type,  2*nonbondeds[type].sigma.value_in_unit(nanometer)/(2**(1/6)), nonbondeds[type].epsilon.value_in_unit(kilojoules_per_mole)))
    else:
       print('  <Atom class="%s" sigma="%.12g" epsilon="%.12g" sigma14="%.12g" epsilon14="%.12g"/>' % (type,  2*nonbondeds[type].sigma.value_in_unit(nanometer)/(2**(1/6)), nonbondeds[type].epsilon.value_in_unit(kilojoules_per_mole), 2*nonbondeds[type].sigma14.value_in_unit(nanometer)/(2**(1/6)), nonbondeds[type].epsilon14.value_in_unit(kilojoules_per_mole)))
for type in nbfixes:
    print('  <NBFixPair class1="%s" class2="%s" sigma="%.16g" epsilon="%.17g"/>' %(nbfixes[type][0], nbfixes[type][1], nbfixes[type][2].value_in_unit(kilojoules_per_mole), nbfixes[type][3].value_in_unit(nanometer)/(2**(1/6))))
print(' </LennardJonesForce>')
##print(' </NonbondedForce>')
print('<MPIDForce>')
for type in atomTypes:
    if type.multipoles[1] == -1 and type.multipoles[2] == -1:
       print('  <Multipole type="%d"' %(type.multipoles[0]))
    else:
       print('  <Multipole type="%d" kz="%d" kx="%d"' %(type.multipoles[0], type.multipoles[1], type.multipoles[2]))
    print('            c0="%.12g" ' %(type.charge) )
    print('            dX="%.12g" dY="%.12g"  dZ="%.12g" ' %(type.multipoles[4], type.multipoles[5], type.multipoles[6]))
    print('            qXX="%.12g" qXY="%.12g" qYY="%.12g" qXZ="%.12g" qYZ="%.12g" qZZ="%.12g" ' %(type.multipoles[7], type.multipoles[8], type.multipoles[9], type.multipoles[10], type.multipoles[11], type.multipoles[12]))
    print('            oXXX="%.12g" oXXY="%.12g" oXYY="%.12g" oYYY="%.12g" oXXZ="%.12g" oXYZ="%.12g" oYYZ="%.12g" oXZZ="%.12g" oYZZ="%.12g" oZZZ="%.12g" ' %(type.multipoles[13], type.multipoles[14], type.multipoles[15], type.multipoles[16], type.multipoles[17], type.multipoles[18], type.multipoles[19], type.multipoles[20], type.multipoles[21], type.multipoles[22]))
    print('            />')
for type in atomTypes:
    print('  <Polarize type="%d" polarizabilityXX="%.12g" polarizabilityYY="%.12g" polarizabilityZZ="%.12g" thole="%.12g" />' %(type.polarize[0], type.polarize[2], type.polarize[3], type.polarize[4], type.polarize[5]))
print('</MPIDForce>')
print('</ForceField>')
