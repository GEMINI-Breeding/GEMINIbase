import { createCrudHooks } from './use-crud'
import { experimentsApi } from '@/api/endpoints/experiments'
import { seasonsApi } from '@/api/endpoints/seasons'
import { sitesApi } from '@/api/endpoints/sites'
import { populationsApi } from '@/api/endpoints/populations'
import { datasetsApi } from '@/api/endpoints/datasets'
import { sensorsApi } from '@/api/endpoints/sensors'
import { sensorPlatformsApi } from '@/api/endpoints/sensor-platforms'
import { sensorTypesApi } from '@/api/endpoints/sensor-types'
import { traitsApi } from '@/api/endpoints/traits'
import { traitLevelsApi } from '@/api/endpoints/trait-levels'
import { plotsApi } from '@/api/endpoints/plots'
import { plantsApi } from '@/api/endpoints/plants'
import { genotypesApi } from '@/api/endpoints/genotypes'
import { variantsApi } from '@/api/endpoints/variants'
import { modelsApi } from '@/api/endpoints/models'
import { scriptsApi } from '@/api/endpoints/scripts'
import { proceduresApi } from '@/api/endpoints/procedures'
import { dataFormatsApi } from '@/api/endpoints/data-formats'
import { dataTypesApi } from '@/api/endpoints/data-types'
import { datasetTypesApi } from '@/api/endpoints/dataset-types'
import type {
  ExperimentOutput, ExperimentInput, ExperimentUpdate,
  SeasonOutput, SeasonInput, SeasonUpdate,
  SiteOutput, SiteInput, SiteUpdate,
  PopulationOutput, PopulationInput, PopulationUpdate,
  DatasetOutput, DatasetInput, DatasetUpdate,
  SensorOutput, SensorInput, SensorUpdate,
  SensorPlatformOutput, SensorPlatformInput, SensorPlatformUpdate,
  SensorTypeOutput, SensorTypeInput, SensorTypeUpdate,
  TraitOutput, TraitInput, TraitUpdate,
  TraitLevelOutput, TraitLevelInput, TraitLevelUpdate,
  PlotOutput, PlotInput, PlotUpdate,
  PlantOutput, PlantInput, PlantUpdate,
  GenotypeOutput, GenotypeInput, GenotypeUpdate,
  VariantOutput, VariantInput, VariantUpdate,
  ModelOutput, ModelInput, ModelUpdate,
  ScriptOutput, ScriptInput, ScriptUpdate,
  ProcedureOutput, ProcedureInput, ProcedureUpdate,
  DataFormatOutput, DataFormatInput, DataFormatUpdate,
  DataTypeOutput, DataTypeInput, DataTypeUpdate,
  DatasetTypeOutput, DatasetTypeInput, DatasetTypeUpdate,
} from '@/api/types'

export const useExperiments = createCrudHooks<ExperimentOutput, ExperimentInput, ExperimentUpdate>('experiments', experimentsApi)
export const useSeasons = createCrudHooks<SeasonOutput, SeasonInput, SeasonUpdate>('seasons', seasonsApi)
export const useSites = createCrudHooks<SiteOutput, SiteInput, SiteUpdate>('sites', sitesApi)
export const usePopulations = createCrudHooks<PopulationOutput, PopulationInput, PopulationUpdate>('populations', populationsApi)
export const useDatasets = createCrudHooks<DatasetOutput, DatasetInput, DatasetUpdate>('datasets', datasetsApi)
export const useSensors = createCrudHooks<SensorOutput, SensorInput, SensorUpdate>('sensors', sensorsApi)
export const useSensorPlatforms = createCrudHooks<SensorPlatformOutput, SensorPlatformInput, SensorPlatformUpdate>('sensorPlatforms', sensorPlatformsApi)
export const useSensorTypes = createCrudHooks<SensorTypeOutput, SensorTypeInput, SensorTypeUpdate>('sensorTypes', sensorTypesApi)
export const useTraits = createCrudHooks<TraitOutput, TraitInput, TraitUpdate>('traits', traitsApi)
export const useTraitLevels = createCrudHooks<TraitLevelOutput, TraitLevelInput, TraitLevelUpdate>('traitLevels', traitLevelsApi)
export const usePlots = createCrudHooks<PlotOutput, PlotInput, PlotUpdate>('plots', plotsApi)
export const usePlants = createCrudHooks<PlantOutput, PlantInput, PlantUpdate>('plants', plantsApi)
export const useGenotypes = createCrudHooks<GenotypeOutput, GenotypeInput, GenotypeUpdate>('genotypes', genotypesApi)
export const useVariants = createCrudHooks<VariantOutput, VariantInput, VariantUpdate>('variants', variantsApi)
export const useModels = createCrudHooks<ModelOutput, ModelInput, ModelUpdate>('models', modelsApi)
export const useScripts = createCrudHooks<ScriptOutput, ScriptInput, ScriptUpdate>('scripts', scriptsApi)
export const useProcedures = createCrudHooks<ProcedureOutput, ProcedureInput, ProcedureUpdate>('procedures', proceduresApi)
export const useDataFormats = createCrudHooks<DataFormatOutput, DataFormatInput, DataFormatUpdate>('dataFormats', dataFormatsApi)
export const useDataTypes = createCrudHooks<DataTypeOutput, DataTypeInput, DataTypeUpdate>('dataTypes', dataTypesApi)
export const useDatasetTypes = createCrudHooks<DatasetTypeOutput, DatasetTypeInput, DatasetTypeUpdate>('datasetTypes', datasetTypesApi)
