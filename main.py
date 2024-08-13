import geopandas as gpd
import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine
import logging

# Configure logging
logging.basicConfig(
    filename='application.log',  # Log file name
    level=logging.INFO,  # Minimum level to log
    format='%(asctime)s - %(levelname)s - %(message)s'  # Log message format
)

def get_engine(db_url):
    """
    Create a SQLAlchemy engine for the database connection.

    :param db_url: Database URL connection string
    :return: SQLAlchemy engine object
    """
    try:
        engine = create_engine(db_url)
        logging.info("Database engine created successfully.")
        return engine
    except SQLAlchemyError as e:
        logging.error(f"Failed to create database engine: {e}")
        raise

def load_vector_layer(engine, table_name, geom_col='geom'):
    """
    Load a vector layer from PostgreSQL into a GeoDataFrame.

    :param engine: SQLAlchemy engine object
    :param table_name: Name of the table in PostgreSQL
    :param geom_col: Name of the geometry column
    :return: GeoDataFrame containing the vector layer
    """
    try:
        query = f"SELECT * FROM {table_name}"
        gdf = gpd.read_postgis(query, engine, geom_col=geom_col)
        logging.info(f"Loaded vector layer '{table_name}' successfully.")
        return gdf
    except Exception as e:
        logging.error(f"Failed to load vector layer '{table_name}': {e}")
        raise

def apply_buffer_and_intersect(land_use_gdf, watercourses_gdf, buffer_distance):
    """
    Apply a buffer to watercourses and intersect with land use data.

    :param land_use_gdf: GeoDataFrame containing land use data
    :param watercourses_gdf: GeoDataFrame containing watercourses data
    :param buffer_distance: Buffer distance in meters
    :return: Filtered GeoDataFrame containing land use regions within the buffer zone
    """
    try:
        # Ensure both layers use the same CRS
        if land_use_gdf.crs != watercourses_gdf.crs:
            watercourses_gdf = watercourses_gdf.to_crs(land_use_gdf.crs)
            logging.info("CRS adjusted to match between layers.")

        # Create a buffer around the watercourses
        watercourses_buffered_gdf = watercourses_gdf.buffer(buffer_distance)

        # Convert the buffered watercourses to a GeoDataFrame
        watercourses_buffered_gdf = gpd.GeoDataFrame(geometry=watercourses_buffered_gdf, crs=land_use_gdf.crs)

        # Perform the intersection with the land use layer
        intersected_land_use_gdf = gpd.overlay(land_use_gdf, watercourses_buffered_gdf, how='intersection')
        logging.info("Applied buffer and intersection successfully.")
        return intersected_land_use_gdf
    except Exception as e:
        logging.error(f"Failed to apply buffer and intersect: {e}")
        raise

def save_geodataframe_to_postgresql(gdf, engine, table_name):
    """
    Save a GeoDataFrame to a PostgreSQL database.

    :param gdf: GeoDataFrame to save
    :param engine: SQLAlchemy engine object
    :param table_name: Name of the table to save data into
    """
    try:
        gdf.to_postgis(name=table_name, con=engine, if_exists='replace', index=False)
        logging.info(f"Data saved to PostgreSQL table: {table_name}")
    except SQLAlchemyError as e:
        logging.error(f"Failed to save GeoDataFrame to PostgreSQL: {e}")
        raise    

def save_geodataframe_to_csv(gdf, file_path):
    """
    Save a GeoDataFrame to a CSV file.

    :param gdf: GeoDataFrame to save
    :param file_path: File path for the CSV file
    """
    try:
        gdf.to_csv(file_path, index=False)
        logging.info(f"Data saved to CSV file: {file_path}")
    except IOError as e:
        logging.error(f"Failed to save GeoDataFrame to CSV: {e}")
        raise

def main(db_url, land_use_table, watercourses_table, buffer_distance, output_table_name, output_csv_file):
    """
    Main function to load data, apply constraints, and save the results.

    :param db_url: Database URL connection string
    :param land_use_table: Name of the land use table in PostgreSQL
    :param watercourses_table: Name of the watercourses table in PostgreSQL
    :param buffer_distance: Buffer distance in meters
    :param output_table_name: Name of the output table in PostgreSQL
    :param output_csv_file: Path to the output CSV file
    """
    try:
        # Create database engine
        engine = get_engine(db_url)

        # Load vector layers from PostgreSQL
        land_use_gdf = load_vector_layer(engine, land_use_table)
        watercourses_gdf = load_vector_layer(engine, watercourses_table)

        # Apply buffer and intersection constraints
        filtered_land_use_gdf = apply_buffer_and_intersect(land_use_gdf, watercourses_gdf, buffer_distance)

        # Save results to PostgreSQL and CSV
        save_geodataframe_to_postgresql(filtered_land_use_gdf, engine, output_table_name)
        save_geodataframe_to_csv(filtered_land_use_gdf, output_csv_file)
    except Exception as e:
        logging.error(f"Failed to complete the main function: {e}")
        raise

if __name__ == "__main__":
    # Define constants
    DATABASE_URL = 'postgresql+psycopg2://postgres:123@localhost:5432/PythonProject'
    LAND_USE_TABLE = 'landuse_10km'
    WATERCOURSES_TABLE = 'rivers_10km'
    BUFFER_DISTANCE = 50  # in meters
    OUTPUT_TABLE_NAME = 'landuse_results'
    OUTPUT_CSV_FILE = 'filtered_land_use_results.csv'

    # Run main function
    main(DATABASE_URL, LAND_USE_TABLE, WATERCOURSES_TABLE, BUFFER_DISTANCE, OUTPUT_TABLE_NAME, OUTPUT_CSV_FILE)