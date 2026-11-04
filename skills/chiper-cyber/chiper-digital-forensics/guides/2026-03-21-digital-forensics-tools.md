# 2026-03-21 Digital Forensics CLI Tools Learning

## Mastered Tools

### 1. SleuthKit - FileSystemforensicsAnalysisToolset
- **Function**: complete FileSystemAnalysisTool，SupportsmultiplekindFileSystemformat
- **CoreTool**: mmls, fsstat, fls, icat, ifind, ils
- **Practical Key Points**:
 - partition tableAnalysisandFileSystemIdentify
 - already deleteFilerecovercomplexandinodeOperation
 - MACwhen timelineGenerationandFilecontentExtract
 - SupportsFAT, NTFS, Ext2/3/4, HFS+, APFSetc.

### 2. Autopsy - digital forensicsplatform
- **Function**: Webinterface digital forensicsplatform，baseatSleuthKit
- **Core Commands**: `autopsy -p port -d evidence_dir`
- **Practical Key Points**:
 - mainThroughWebinterfaceOperation
 - Commandrowused forservicestartandConfiguration
 - SupportsmultipleUsercollaborationandcasemanagement
 - RequirescoordinateSleuthKitUse

### 3. Scalpel - FilecarvingTool
- **Function**: baseatFilehead尾signature Filecarving
- **Core Commands**: `scalpel -c config.conf -o output_dir image`
- **Practical Key Points**:
 - Configuration FilesdefinitionFilesignature
 - Supports预览modeandactualcarving
 - handling重叠andfragmentizeFile
 - 兼容Foremostformat

### 4. Bulk Extractor - highitycandigital forensicsTool
- **Function**: parallelScanningExtractspecificDataType
- **Core Commands**: `bulk_extractor -e scanner -o output image`
- **Practical Key Points**:
 - multi-threadedhighitycanhandling
 - Supports50+kindScanningtool（email, url, credit_cardetc.）
 - onbelowtextwindowandpart页handling
 - automated GenerationstructureizeOutput

### 5. ExifTool - metaDataAnalysisTool
- **Function**: read、write、编辑200+kindFileformat metaData
- **Core Commands**: `exiftool -tags file` or `exiftool -json file`
- **Practical Key Points**:
 - Supportsdiagram像、viewfrequency、documentation、音frequencyetc.format
 - batchamounthandlingandrecursivehandling
 - metaDatamodifyanddelete
 - JSON/CSVformatOutput

### 6. PhotoRec - DatarecovercomplexTool
- **Function**: baseatFilesignature Datarecovercomplex
- **Core Commands**: `photorec -d recovery_dir image`
- **Practical Key Points**:
 - Supports480+kindFileformat
 - ignoreFileSystemdirectScanningdisk
 - 智canhandlingfragmentizeFile
 - interactiveandCommandrowmode

### 7. TestDisk - partzonerecovercomplexTool
- **Function**: partition tablefixcomplexand丢失partzonerecovercomplex
- **Core Commands**: `testdisk /list image` orinteractivemode
- **Practical Key Points**:
 - partition tableAnalysisandfixcomplex
 - introduceguide扇zonefixcomplex
 - multipleFileSystemSupports
 - interactiveOperationasmain

## Tool Combination Strategies

### complete forensicsWorkflow
1. **diskAnalysis**: mmls + fsstat
2. **FileSystemAnalysis**: fls + icat
3. **Filecarving**: scalpel + photorec
4. **metaDataAnalysis**: exiftool
5. **specificData Extraction**: bulk_extractor

### quick ResponseWorkflow
- 紧急Datarecovercomplex: photorec
- criticalinformationExtract: bulk_extractor
- partzonefixcomplex: testdisk

### deepdegreeAnalysisWorkflow
- detailed FileSystemAnalysis: SleuthKitallsetTool
- metaDatarelatedAnalysis: exiftool + bulk_extractor
- Networkactivityrebuild: bulk_extractorNetworkrelatedScanningtool

## Practical Notes

### Legal and Ethical
- alwaysobtaincombinemethodauthorization
- maintainevidencechainintegrity
- Useonlyreadmethodhandlingrawevidence
- recordall OperationSteps

### Technical Best Practices
- createrawevidence hashValue
- Usewriteprotectdevice
- in副thisonperformAnalysis
- VerificationToolOutput accurateity

### Performance Optimization
- based onevidencesizeselectappropriate Tool
- Usemulti-threadedToolImprove Efficiency
- combinereasonpartmatchSystemresource
- monitoringdisk空intervalUse

## File Locations
- Detailed Command Reference: `/home/parallels/.chiper/workspace/security-tools-67/digital-forensics-cli-reference.md`
- This learning record: Current file
- Tool classification statistics: `/home/parallels/.chiper/workspace/kali-517-analysis/`

## Follow-up Learning Plan
- deep LearningnolineSecurityTool（kismet, aircrack-ng, reaveretc.）
- MasterafterpenetrationTool（mimikatz, crackmapexec, bloodhoundetc.）
- LearningPasswordAttackTool（hashcat, johnetc.）