from gemini.api.experiment import Experiment
from gemini.api.season import Season
from gemini.api.site import Site
from gemini.api.sensor_platform import SensorPlatform
from gemini.api.sensor import Sensor

import os, re, logging
from typing import List
from dataclasses import dataclass
from datetime import datetime, date
from tqdm import tqdm
import json

logger = logging.getLogger(__name__)


class AMIGAPhoneParser:

    gemini_experiment : Experiment = None
    gemini_experiment_sites : List[Site] = None
    gemini_experiment_seasons : List[Season] = None
    gemini_amiga_sensor_platform : SensorPlatform = None
    gemini_amiga_sensors : List[Sensor] = None

    def __init__(self):
        gemini_experiment = Experiment.get(experiment_name="GEMINI")
        gemini_experiment_sites = gemini_experiment.get_sites()
        if gemini_experiment_sites:
            self.gemini_experiment_sites = gemini_experiment_sites
        gemini_experiment_seasons = gemini_experiment.get_seasons()
        if gemini_experiment_seasons:
            self.gemini_experiment_seasons = gemini_experiment_seasons
        gemini_amiga_sensor_platform = SensorPlatform.get(
            experiment_name="GEMINI",
            sensor_platform_name="AMIGA"
        )
        if gemini_experiment:
            self.gemini_experiment = gemini_experiment
        if gemini_amiga_sensor_platform:
            self.gemini_amiga_sensor_platform = gemini_amiga_sensor_platform
        gemini_amiga_sensors = gemini_amiga_sensor_platform.get_sensors()
        if gemini_amiga_sensors:
            self.gemini_amiga_sensors = gemini_amiga_sensors
        logger.info("Initialized AMIGAPhoneParser with GEMINIbase experiment data from database.")


    def validate(self, data_directory: str) -> bool:
        pattern = r"(?:\.[\\/])?Dataset_(\d{4})[\\/]([^\\/]+)[\\/](\d{4}-\d{2}-\d{2})[\\/]Amiga_Phone[\\/]Phone$"
        if not bool(re.search(pattern, data_directory)):
            logger.warning("Invalid data directory structure.")
            return False

        # Metadata directory is required
        metadata_dir = os.path.join(data_directory, 'meta_json')
        if not os.path.exists(metadata_dir):
            logger.warning("Metadata directory does not exist.")
            return False

        # Optional sensor directories — warn but do not fail if absent
        optional_dirs = {
            'confidence_tiff': 'Confidence',
            'depth_tiff': 'Depth',
            'flir_jpg': 'FLIR',
            'rgb_jpeg': 'RGB',
        }
        for dir_name, label in optional_dirs.items():
            dir_path = os.path.join(data_directory, dir_name)
            if not os.path.exists(dir_path):
                logger.info(f"{label} directory does not exist — skipping {label} data.")

        return True

    def parse(self, data_directory: str):

        if not self.validate(data_directory):
            return

        # Extract year, site, and collection_date from path via the validated pattern
        pattern = r"Dataset_(\d{4})[\\/]([^\\/]+)[\\/](\d{4}-\d{2}-\d{2})[\\/]Amiga_Phone[\\/]Phone"
        match = re.search(pattern, data_directory)
        year = match.group(1)
        site = match.group(2)
        collection_date = match.group(3)
        logger.info(f"Parsing: year={year}, site={site}, collection_date={collection_date}")

        # data_by_number: dict keyed by 5-digit file index for correlation across sensor types
        data_by_number = {}

        # Collect Metadata
        metadata_dir = os.path.join(data_directory, 'meta_json')
        for metadata_file_name in tqdm(os.listdir(metadata_dir), desc="Collecting Metadata Files"):
            if 'collection' in metadata_file_name:
                continue
            metadata_file = os.path.join(metadata_dir, metadata_file_name)
            with open(metadata_file, 'r') as f:
                metadata = json.loads(f.read())
                file_number = int(metadata_file_name.split('.')[0][-5:])
                timestamp = float(metadata['info']['epochTime'])
                timestamp = datetime.fromtimestamp(timestamp)
                data_by_number[file_number] = {
                    'timestamp': timestamp,
                    'metadata': metadata,
                    'metadata_file': os.path.abspath(metadata_file)
                }

        # Collect Confidence
        confidence_dir = os.path.join(data_directory, 'confidence_tiff')
        if os.path.exists(confidence_dir):
            for confidence_file_name in tqdm(os.listdir(confidence_dir), desc="Collecting Confidence Files"):
                if 'collection' in confidence_file_name:
                    continue
                confidence_file = os.path.join(confidence_dir, confidence_file_name)
                file_number = int(confidence_file_name.split('.')[0][-5:])
                if file_number in data_by_number:
                    data_by_number[file_number]['confidence_file'] = os.path.abspath(confidence_file)

        # Collect Depth
        depth_dir = os.path.join(data_directory, 'depth_tiff')
        if os.path.exists(depth_dir):
            for depth_file_name in tqdm(os.listdir(depth_dir), desc="Collecting Depth Files"):
                if 'collection' in depth_file_name:
                    continue
                depth_file = os.path.join(depth_dir, depth_file_name)
                file_number = int(depth_file_name.split('.')[0][-5:])
                if file_number in data_by_number:
                    data_by_number[file_number]['depth_file'] = os.path.abspath(depth_file)

        # Collect FLIR
        flir_dir = os.path.join(data_directory, 'flir_jpg')
        if os.path.exists(flir_dir):
            for flir_file_name in tqdm(os.listdir(flir_dir), desc="Collecting FLIR Files"):
                if 'collection' in flir_file_name:
                    continue
                flir_file = os.path.join(flir_dir, flir_file_name)
                file_number = int(flir_file_name.split('.')[0][-5:])
                if file_number in data_by_number:
                    data_by_number[file_number]['flir_file'] = os.path.abspath(flir_file)

        # Collect RGB
        rgb_dir = os.path.join(data_directory, 'rgb_jpeg')
        if os.path.exists(rgb_dir):
            for rgb_file_name in tqdm(os.listdir(rgb_dir), desc="Collecting RGB Files"):
                if 'collection' in rgb_file_name:
                    continue
                rgb_file = os.path.join(rgb_dir, rgb_file_name)
                file_number = int(rgb_file_name.split('.')[0][-5:])
                if file_number in data_by_number:
                    data_by_number[file_number]['rgb_file'] = os.path.abspath(rgb_file)

        data_map = {
            'collection_date': collection_date,
            'season': year,
            'site': site,
            'data': list(data_by_number.values()),
        }

        self.upload_metadata_files(data_map)
        self.upload_confidence_files(data_map)
        self.upload_depth_files(data_map)
        self.upload_flir_files(data_map)
        self.upload_rgb_files(data_map)


    def upload_metadata_files(self, data_map: dict):
        metadata_sensor = Sensor.get(sensor_name="AMIGA Phone Camera Metadata", experiment_name="GEMINI")
        data_records = sorted(data_map['data'], key=lambda x: x['timestamp'])
        data_records = data_records[:100]
        data_timestamps = [record['timestamp'] for record in data_records]
        data_record_files = [record['metadata_file'] for record in data_records if 'metadata_file' in record]
        experiment_name = self.gemini_experiment.experiment_name
        season_name = data_map['season']
        site_name = data_map['site']

        metadata_sensor.add_records(
            timestamps=data_timestamps,
            collection_date=data_map['collection_date'],
            experiment_name=experiment_name,
            season_name=season_name,
            site_name=site_name,
            record_files=data_record_files
        )

    def upload_confidence_files(self, data_map: dict):
        confidence_sensor = Sensor.get(sensor_name="AMIGA Phone Confidence", experiment_name="GEMINI")
        data_records = sorted(data_map['data'], key=lambda x: x['timestamp'])
        data_records = data_records[:100]
        data_timestamps = [record['timestamp'] for record in data_records]
        data_record_files = [record['confidence_file'] for record in data_records if 'confidence_file' in record]
        experiment_name = self.gemini_experiment.experiment_name
        season_name = data_map['season']
        site_name = data_map['site']

        confidence_sensor.add_records(
            timestamps=data_timestamps,
            collection_date=data_map['collection_date'],
            experiment_name=experiment_name,
            season_name=season_name,
            site_name=site_name,
            record_files=data_record_files
        )

    def upload_depth_files(self, data_map: dict):
        depth_sensor = Sensor.get(sensor_name="AMIGA Phone Depth Sensor", experiment_name="GEMINI")
        data_records = sorted(data_map['data'], key=lambda x: x['timestamp'])
        data_records = data_records[:100]
        data_timestamps = [record['timestamp'] for record in data_records]
        data_record_files = [record['depth_file'] for record in data_records if 'depth_file' in record]
        experiment_name = self.gemini_experiment.experiment_name
        season_name = data_map['season']
        site_name = data_map['site']

        depth_sensor.add_records(
            timestamps=data_timestamps,
            collection_date=data_map['collection_date'],
            experiment_name=experiment_name,
            season_name=season_name,
            site_name=site_name,
            record_files=data_record_files
        )

    def upload_flir_files(self, data_map: dict):
        flir_sensor = Sensor.get(sensor_name="AMIGA Phone Thermal Camera", experiment_name="GEMINI")
        data_records = sorted(data_map['data'], key=lambda x: x['timestamp'])
        data_records = data_records[:100]
        data_timestamps = [record['timestamp'] for record in data_records]
        data_record_files = [record['flir_file'] for record in data_records if 'flir_file' in record]
        experiment_name = self.gemini_experiment.experiment_name
        season_name = data_map['season']
        site_name = data_map['site']

        flir_sensor.add_records(
            timestamps=data_timestamps,
            collection_date=data_map['collection_date'],
            experiment_name=experiment_name,
            season_name=season_name,
            site_name=site_name,
            record_files=data_record_files
        )

    def upload_rgb_files(self, data_map: dict):
        rgb_sensor = Sensor.get(sensor_name="AMIGA Phone RGB Camera", experiment_name="GEMINI")
        data_records = sorted(data_map['data'], key=lambda x: x['timestamp'])
        data_records = data_records[:100]
        data_timestamps = [record['timestamp'] for record in data_records]
        data_record_files = [record['rgb_file'] for record in data_records if 'rgb_file' in record]
        experiment_name = self.gemini_experiment.experiment_name
        season_name = data_map['season']
        site_name = data_map['site']

        rgb_sensor.add_records(
            timestamps=data_timestamps,
            collection_date=data_map['collection_date'],
            experiment_name=experiment_name,
            season_name=season_name,
            site_name=site_name,
            record_files=data_record_files
        )
