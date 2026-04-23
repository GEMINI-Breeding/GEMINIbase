from enum import Enum

from enum import Enum

class GEMINIDataFormat(Enum):
  """
  Enum class representing the data formats supported by the GEMINIbase.

  Attributes:
    Default (int): Default data format.
    TXT (int): Text file format.
    JSON (int): JSON file format.
    CSV (int): CSV file format.
    TSV (int): TSV (Tab-separated values) file format.
    XML (int): XML file format.
    HTML (int): HTML file format.
    PDF (int): PDF file format.
    JPEG (int): JPEG image format.
    PNG (int): PNG image format.
    GIF (int): GIF image format.
    BMP (int): BMP image format.
    TIFF (int): TIFF image format.
    WAV (int): WAV audio format.
    MP3 (int): MP3 audio format.
    MPEG (int): MPEG video format.
    AVI (int): AVI video format.
    MP4 (int): MP4 video format.
    OGG (int): OGG audio format.
    WEBM (int): WEBM video format.
    NPY (int): NPY (NumPy array) format.
  """
  Default = 0
  TXT = 1
  JSON = 2
  CSV = 3
  TSV = 4
  XML = 5
  HTML = 6
  PDF = 7
  JPEG = 8
  PNG = 9
  GIF = 10
  BMP = 11
  TIFF = 12
  WAV = 13
  MP3 = 14
  MPEG = 15
  AVI = 16
  MP4 = 17
  OGG = 18
  WEBM = 19
  NPY = 20

from enum import Enum

class GEMINISensorType(Enum):
  """
  Enumeration representing different types of sensors in the GEMINIbase.

  Attributes:
    Default (int): Default sensor type.
    RGB (int): RGB sensor type.
    NIR (int): NIR (Near Infrared) sensor type.
    Thermal (int): Thermal sensor type.
    Multispectral (int): Multispectral sensor type.
    Weather (int): Weather sensor type.
    GPS (int): GPS sensor type.
    Calibration (int): Calibration sensor type.
    Depth (int): Depth sensor type.
    IMU (int): IMU (Inertial Measurement Unit) sensor type.
    Disparity (int): Disparity sensor type.
    Confidence (int): Confidence sensor type.
  """
  Default = 0
  RGB = 1
  NIR = 2
  Thermal = 3
  Multispectral = 4
  Weather = 5
  GPS = 6
  Calibration = 7
  Depth = 8
  IMU = 9
  Disparity = 10
  Confidence = 11

from enum import Enum

class GEMINIDatasetType(Enum):
  """
  Enum representing the types of datasets in the GEMINIbase.

  Attributes:
    Default (int): Default dataset type.
    Sensor (int): Sensor dataset type.
    Trait (int): Trait dataset type.
    Script (int): Script dataset type.
    Model (int): Model dataset type.
    Procedure (int): Procedure dataset type.
    Other (int): Other dataset type.
  """
  Default = 0
  Sensor = 1
  Trait = 2
  Script = 3
  Model = 4
  Procedure = 5
  Other = 6

class GEMINIDataType(Enum):
  """
  Enumeration representing different data types in the GEMINIbase.

  Attributes:
    Default (int): Default data type.
    Text (int): Text data type.
    Web (int): Web data type.
    Document (int): Document data type.
    Image (int): Image data type.
    Audio (int): Audio data type.
    Video (int): Video data type.
    Binary (int): Binary data type.
    Other (int): Other data type.
  """
  Default = 0
  Text = 1
  Web = 2
  Document = 3
  Image = 4
  Audio = 5
  Video = 6
  Binary = 7
  Other = 8

from enum import Enum

class GEMINITraitLevel(Enum):
  """
  Enum representing the trait levels in the Gemini framework.

  Attributes:
    Default (int): Default trait level.
    Plot (int): Plot trait level.
    Plant (int): Plant trait level.
  """
  Default = 0
  Plot = 1
  Plant = 2

