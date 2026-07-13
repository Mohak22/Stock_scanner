# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 11:03:40 2026

@author: mohak
"""

from pathlib import Path
import pandas as pd 

from reports.excel_report_generator import (
    save_output
)

from config.paths import PROCESSED_BHAVCOPY_FOLDER

class BhavcopyCleaner:
    COLUMN_MAPPING = {
        "DATE1": "TIMESTAMP",
        "CLOSE_PRICE": "CLOSE",
        "TTL_TRD_QNTY": "TOTTRDQTY",
        "TURNOVER_LACS": "TOTTRDVAL"
    }
    
    REQUIRED_COLUMNS = ("SYMBOL", "SERIES", "CLOSE", "TOTTRDQTY", "TOTTRDVAL", "TIMESTAMP", "DELIV_QTY", "DELIV_PER")

    def __init__(

        self,

        processed_directory: Path

    ):

        self.processed_directory = processed_directory

        self.processed_directory.mkdir(

            parents=True,

            exist_ok=True

        )

    def _read_raw_file(
        self,
        raw_file_path: Path
    ) -> pd.DataFrame:
    
        print(
            f"\nReading : {raw_file_path.name}"
        )
    
        return pd.read_csv(
            raw_file_path, low_memory = False
        )
    
    def clean_file(
        self,
        raw_file_path: Path
    ) -> Path:
    
        output_path = (
            self.processed_directory
            / raw_file_path.with_suffix(".parquet").name
        )
    
        if output_path.exists():
    
            print(
                f"\nProcessed file already exists : {output_path.name}"
            )
    
            return output_path
    
        dataframe = self._read_raw_file(
            raw_file_path
        )
        
        dataframe.columns = dataframe.columns.str.strip()
        
        dataframe = dataframe.rename(
            columns=self.COLUMN_MAPPING
        )

        string_columns = dataframe.select_dtypes(
            include="object"
        ).columns
        
        dataframe[string_columns] = dataframe[
            string_columns
        ].apply(
            lambda column: column.str.strip()
        )
        
        self._validate_columns(
            dataframe
        )

        dataframe = self._clean_dataframe(
            dataframe
        )

        return self._save_processed_file(
            dataframe,
            raw_file_path
        )
    
    def _validate_columns(
        self,
        dataframe: pd.DataFrame
    ):
    
        missing_columns = [
    
            column
    
            for column in self.REQUIRED_COLUMNS
    
            if column not in dataframe.columns
    
        ]
    
        if missing_columns:
    
            raise ValueError(
    
                f"Missing columns : {missing_columns}"
    
            )
                
    def _clean_dataframe(
        self,
        dataframe: pd.DataFrame
    ) -> pd.DataFrame:
    
        dataframe = dataframe[
            list(self.REQUIRED_COLUMNS)
        ].copy()
    
        dataframe = dataframe[
            dataframe["SERIES"] == "EQ"
        ].copy()
    
        if dataframe.empty:
    
            raise ValueError(
                "No EQ series found in raw bhavcopy."
            )
            
        dataframe["TIMESTAMP"] = (
            dataframe["TIMESTAMP"]
            .astype(str)
            .str.strip()
        )    

        dataframe["TIMESTAMP"] = pd.to_datetime(
            dataframe["TIMESTAMP"],
            format="%d-%b-%Y"
        )
    
        numeric_columns = (
            "CLOSE",
            "TOTTRDQTY",
            "TOTTRDVAL",
            "DELIV_QTY",
            "DELIV_PER"
        )
    
        dataframe[list(numeric_columns)] = dataframe[
            list(numeric_columns)
        ].apply(
            pd.to_numeric,
            errors="coerce"
        )
    
        dataframe = dataframe.dropna(
            subset=[
                "SYMBOL",
                "TIMESTAMP",
                "CLOSE",
                "TOTTRDQTY",
                "TOTTRDVAL",
                "DELIV_QTY",
                "DELIV_PER"
            ]
        )
    
        dataframe = dataframe.drop_duplicates()
    
        dataframe = dataframe.sort_values(
            by=["SYMBOL", "TIMESTAMP"]
        )
    
        dataframe = dataframe.reset_index(
            drop=True
        )
    
        return dataframe
    
    def _save_processed_file(
        self,
        dataframe: pd.DataFrame,
        raw_file_path: Path
    ) -> Path:
    
        file_name = raw_file_path.with_suffix(
            ".parquet"
        ).name
    
        save_output(
    
            dataframe=dataframe,
    
            folder_name=PROCESSED_BHAVCOPY_FOLDER,
    
            file_name=file_name,
    
            save_output=True
    
        )
    
        return (
            self.processed_directory
            / file_name
        )