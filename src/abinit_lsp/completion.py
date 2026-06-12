"""Keyword completion for ABINIT input files.

Provides completion candidates for ABINIT keywords, with optional prefix
filtering and dataset-aware suggestions.
"""

from __future__ import annotations

# Comprehensive keyword documentation for ABINIT.
# Source: ABINIT documentation https://docs.abinit.org/variables/
# Manifest: raw/assets/upstream-sources.md maps each keyword to its canonical docs URL.
KEYWORD_DOCS: dict[str, str] = {
    "acell": (
        "acell : Scale of the primitive vectors (in atomic units).\n"
        "Specifies the lengths of the three lattice vectors. Use 3*val for cubic cells."
    ),
    "amu": (
        "amu : Atomic mass units.\n"
        "Defines the atomic masses for each atom type, in atomic mass units."
    ),
    "diemac": (
        "diemac : Macroscopic dielectric constant.\n"
        "Used for screening in response function calculations. Typical ~12 for Si."
    ),
    "ecut": (
        "ecut : Plane-wave energy cutoff in Hartree.\n"
        "Controls the basis set size. Must be converged for reliable results. "
        "Typical values: 10-50 Ha depending on pseudopotential."
    ),
    "ixc": (
        "ixc : Exchange-correlation functional index.\n"
        "1 = LDA (Teter), 11 = GGA (PBE). See ABINIT docs for full list."
    ),
    "kptopt": (
        "kptopt : k-point generation option.\n"
        "1 = full grid, 0 = list of k-points, -1 = half grid (time-reversal)."
    ),
    "natom": (
        "natom : Number of atoms in the unit cell.\n"
        "Must be a positive integer. Determines dimension of many arrays."
    ),
    "nband": (
        "nband : Number of electronic bands.\n"
        "Must be >= number of occupied states. Extra bands for metals/insulators."
    ),
    "ngkpt": (
        "ngkpt : Number of k-points in each direction.\n"
        "Three integers defining the Monkhorst-Pack grid: ngkpt1 ngkpt2 ngkpt3."
    ),
    "nstep": (
        "nstep : Maximum number of SCF iterations.\n"
        "The SCF loop will stop after this many steps even if not converged."
    ),
    "ntypat": ("ntypat : Number of atom types.\nDetermines the dimension of znucl, amu arrays."),
    "occopt": (
        "occopt : Occupation scheme option.\n"
        "1 = fixed occupations (insulators), 3 = Fermi-Dirac smearing, "
        "7 = Methfessel-Paxton."
    ),
    "optcell": (
        "optcell : Cell optimization mode.\n"
        "0 = no cell optimization, 1 = full optimization, 2 = constant volume."
    ),
    "pseudos": (
        "pseudos : Pseudopotential file names.\n"
        "Names or paths of pseudopotential files for each atom type."
    ),
    "rprim": (
        "rprim : Real space primitive vectors (dimensionless).\n"
        "3x3 matrix (rprim1, rprim2, rprim3) defining lattice geometry. "
        "Common: FCC [0 0.5 0.5, 0.5 0 0.5, 0.5 0.5 0]."
    ),
    "toldfe": (
        "toldfe : Tolerance on total energy for SCF convergence (Hartree).\n"
        "SCF stops when energy change < toldfe between iterations."
    ),
    "tolmxf": (
        "tolmxf : Tolerance on maximum force for geometry convergence (Hartree/Bohr).\n"
        "Structural relaxation stops when max force < tolmxf."
    ),
    "typat": (
        "typat : Type of each atom.\nInteger array mapping each atom to its type index (1-based)."
    ),
    "xred": (
        "xred : Reduced (fractional) coordinates of atoms.\n"
        "N x 3 array of atomic positions in fractional coordinates."
    ),
    "xcart": (
        "xcart : Cartesian coordinates of atoms (Bohr).\n"
        "N x 3 array of atomic positions in Cartesian coordinates."
    ),
    "znucl": (
        "znucl : Nuclear charge (atomic number) for each atom type.\n"
        "Determines the pseudopotential and chemical identity."
    ),
    "ndtset": (
        "ndtset : Number of datasets.\nEnables multi-dataset calculations with keywordN syntax."
    ),
    "shiftk": (
        "shiftk : Shift of the k-point grid.\n"
        "Three values per shift, can be multiple sets. Default: 0.5 0.5 0.5."
    ),
    "nshiftk": (
        "nshiftk : Number of k-point grid shifts.\nNumber of shift vectors provided in shiftk."
    ),
    "iscf": ("iscf : SCF algorithm choice.\n1 = standard, 2 =Anderson, 5 = CG, 7 = Pulay mixing."),
    "prtvol": ("prtvol : Volume of output printing.\n0 = minimal, 1 = normal, 2 = verbose."),
    "tolvrs": (
        "tolvrs : Tolerance on the potential residual for SCF convergence.\n"
        "Alternative to toldfe for convergence criterion."
    ),
    "prtstd": (
        "prtstd : Standard output printing level.\n"
        "Controls the amount of information written to output."
    ),
    "getden": (
        "getden : Dataset from which to read the density.\n"
        "Integer or -1 (from previous dataset). Used in chained calculations."
    ),
    "getwfk": (
        "getwfk : Dataset from which to read the wavefunctions.\n"
        "Integer or -1 (from previous dataset). Used in chained calculations."
    ),
    "irdwfk": (
        "irdwfk : Flag to read wavefunctions from disk.\n1 = read from file, 0 = do not read."
    ),
    "irdden": ("irdden : Flag to read density from disk.\n1 = read from file, 0 = do not read."),
    "prtden": ("prtden : Flag to write the density to disk.\n1 = write density file after SCF."),
    "prtwf": (
        "prtwf : Flag to write wavefunctions to disk.\n1 = write wavefunction file after SCF."
    ),
    "prt1dm": (
        "prt1dm : Flag to write 1D pseudopotential in machine-readable format.\n"
        "Useful for debugging pseudopotential parameters."
    ),
    "fband": (
        "fband : Fraction of extra bands.\n"
        "When nband is not set, determines extra bands as fraction of occupied."
    ),
    "nline": (
        "nline : Number of line minimizations per band.\n"
        "Controls convergence of individual band updates."
    ),
    "npulayit": (
        "npulayit : Number of Pulay iterations for SCF mixing.\n"
        "Controls history depth in Pulay/Anderson mixing."
    ),
    "diemix": (
        "diemix : Mixing parameter for the dielectric matrix.\n"
        "Controls SCF mixing strength. Typical: 0.5-2.0."
    ),
    "dtset": (
        "dtset : Index of the current dataset.\nUsed internally in multi-dataset calculations."
    ),
    "jdtset": (
        "jdtset : List of dataset indices to compute.\n"
        "Array of integers selecting which datasets to run."
    ),
    "udtset": (
        "udtset : Number of datasets in each 'super-dataset' group.\n"
        "Used for more complex multi-dataset workflows."
    ),
    "ecutsm": (
        "ecutsm : Energy cutoff smoothing (Hartree).\n"
        "Smooths the plane-wave cutoff to improve convergence. "
        "Typical: 0.5 Ha."
    ),
    "dilatmx": (
        "dilatmx : Maximum allowed dilation factor for cell optimization.\n"
        "Pre-allocates plane-wave sphere for cell changes. Default: 1.0."
    ),
    "chkprim": (
        "chkprim : Check for primitive cell.\n"
        "0 = allow non-primitive cells, 1 = enforce primitive cell."
    ),
    "usepaw": (
        "usepaw : Flag to use PAW formalism.\n"
        "1 = use PAW, 0 = use norm-conserving pseudopotentials."
    ),
    "npsp": ("npsp : Number of pseudopotential files.\nShould match ntypat."),
    "ppdirpath": (
        "ppdirpath : Path to pseudopotential directory.\n"
        "Directory containing pseudopotential files."
    ),
    "autoparal": (
        "autoparal : Enable automatic parallelization setup.\n"
        "1 = let ABINIT choose parallel distribution automatically."
    ),
    "npkpt": (
        "npkpt : Number of processors for k-point parallelization.\n"
        "Must divide total number of k-points evenly."
    ),
    "npband": (
        "npband : Number of processors for band parallelization.\nMust divide nband evenly."
    ),
    "npfft": (
        "npfft : Number of processors for FFT parallelization.\n"
        "Controls parallel distribution of plane-wave operations."
    ),
}

# All known keywords (union of various sources)
ALL_KEYWORDS: list[str] = sorted(
    {
        "acell",
        "amu",
        "autoparal",
        "chkprim",
        "diemac",
        "diemix",
        "dilatmx",
        "dtset",
        "ecut",
        "ecutsm",
        "fband",
        "getden",
        "getwfk",
        "irdwfk",
        "irdden",
        "iscf",
        "ixc",
        "jdtset",
        "kptopt",
        "natom",
        "nband",
        "ndtset",
        "ngkpt",
        "nline",
        "npband",
        "npfft",
        "npkpt",
        "npsp",
        "nshiftk",
        "nstep",
        "ntypat",
        "occopt",
        "optcell",
        "ppdirpath",
        "prtden",
        "prt1dm",
        "prtstd",
        "prtvolf",
        "prtwf",
        "pseudos",
        "rprim",
        "shiftk",
        "toldfe",
        "tolmxf",
        "tolvrs",
        "typat",
        "udtset",
        "usepaw",
        "xcart",
        "xred",
        "znucl",
    }
)


def complete_keywords(prefix: str) -> list[dict[str, str]]:
    """Return completion items for ABINIT keywords matching *prefix*.

    Each item is a dict with keys ``keyword``, ``kind``, and ``doc``.
    """
    prefix_lower = prefix.lower()
    results: list[dict[str, str]] = []
    for kw in ALL_KEYWORDS:
        if kw.startswith(prefix_lower):
            results.append(
                {
                    "keyword": kw,
                    "kind": "keyword",
                    "doc": KEYWORD_DOCS.get(kw, ""),
                }
            )
    return results
