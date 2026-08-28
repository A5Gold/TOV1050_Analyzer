This tool is for analyzing the data, i am planning to use the exact algorithm from 'TOV640_Analyzer' program on a separate program or integrate it into the existing program (Let me know which approach is better). The problem for TOV1050 is the raw data format and variable header is a little bit different from TOV640. Understand the difference and provide a development plan, let me know if it is better to isolate the TOV1050_Analyzer folder from TOV640_Analyzer to avoid changing the existing program. If so, provide the prompt for me to start in the new project, and ask the chatbox to refer back to the TOV640_Analyzer folder document.

You can use subagent in the task.
### Reference Document
Folder: C:\Smart Maintanence\TOV640_Analyzer\docs\TOV1050_Migration
Variable Mapping: Variable Mapping with TOV640_Analyzer.xlsx
TOV640_Analyzer Program Architecture and algorithm: TOV640_Analyzer\docs\architecture.md
Existing TOV1050 Raw data: \Raw data
Existing TOV1050 config: \config\ (inside the folder there are every line metadata [ISL metadata.xlsx])

### Line of TOV640 and TOV1050

TOV640: EAL, TML
TOV1050: AEL, TCL, DRL, KTL, ISL, TWL, KTL, TKL

### Session of TOV640 and TOV1050
Mainline: every line default session
EAL: Mainline, RAC, LMC, LOW
TKL: Mainline, TKS
DRL: Mainline, Passing Loop (PL)

### Data pre process
You may refer to the TOV640_Analyzer to understand how to expect and the format for the program, and then when user upload the raw data (.csv) to the new TOV1050_Analyzer program, the program will auto perform data clean and pre-process to fit the program algorithm.

### Chainage
In the raw data of TOV640 (.datac), the Chainage is calculated by 'Merge "KM" and "LOCATION"', but in the raw data of TOV1050 (.csv), the Chainage is already pre-process and can directly refer to "Km". (This has stated in Variable Mapping file)

### raw data file size
TOV640: 10 MB, 50000 row
TOV1050: 150 MB, 900000 row
- in TOV1050: "1.#IO" value is the default empty return value from the hardware, which can be ignore.
** in TOV1050: The first 100 row and end 100 row is usually the start up and end value which cannot be used and need to be ignore.
