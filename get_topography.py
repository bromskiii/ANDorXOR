import pandas as pd
import numpy as np
import os
from typing import Optional, Dict, Union

def haversine_distance(lat1_rad, lon1_rad, lat2_rad, lon2_rad, earth_radius_m=6371000):
    """
    Calculates the Haversine distance between two points (in radians) on Earth.
    Returns the distance in meters.
    """
    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad
    
    a = np.sin(delta_lat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    distance = earth_radius_m * c
    return distance

def analyze_and_export_metrics(
    file_path: str, 
    lon_col: str = 'x', 
    lat_col: str = 'y',
    z_col: str = 'ZCOORD',
    id_col: str = 'ID', # Assumes an 'ID' or 'OBJECTID' column exists for ordering
    output_filename: Optional[str] = None
) -> Optional[Dict[str, Union[float, str]]]:
    """
    Analyzes raw elevation data (Lon/Lat/Alt) to determine key terrain parameters.
    
    This function loads (X, Y, Z) points, calculates the true 3D distance and slope
    using the Haversine formula, and returns Mean, Median (robust), and Maximum (worst-case)
    metrics for reliable vehicle design.
    """
    
    print(f"--- Initiating Robust Quantitative Terrain Analysis for: {os.path.basename(file_path)} ---")
    
    # 1. Load the data
    try:
        df = pd.read_excel(file_path)
    except FileNotFoundError:
        print(f"ERROR: We couldn't locate the file at '{file_path}'. Please verify the path and file name.")
        return None
    except Exception as e:
        print(f"ERROR: An unexpected issue occurred while trying to load the Excel file: {e}")
        return None
        
    # Check for empty data or missing columns
    required_cols = [lon_col, lat_col, z_col, id_col]
    if df.empty or not all(col in df.columns for col in required_cols):
        print(f"ERROR: Data is empty or missing required columns ({', '.join(required_cols)}).")
        return None

    # --- Step 1: Calculate True Distance and Slope ---
    
    # Sort by the ID column to process points in their intended sequence
    df = df.sort_values(by=id_col).reset_index(drop=True)
    
    # Get previous point's data using .shift()
    df['prev_lat'] = df[lat_col].shift(1)
    df['prev_lon'] = df[lon_col].shift(1)
    
    # Convert degrees to radians for Haversine calculation
    df['lat_rad'] = np.radians(df[lat_col])
    df['lon_rad'] = np.radians(df[lon_col])
    df['prev_lat_rad'] = np.radians(df['prev_lat'])
    df['prev_lon_rad'] = np.radians(df['prev_lon'])
    
    # Calculate true horizontal distance (d_horizontal) and vertical change (dZ)
    df['d_horizontal_m'] = haversine_distance(
        df['prev_lat_rad'], df['prev_lon_rad'],
        df['lat_rad'], df['lon_rad']
    )
    df['dZ_m'] = df[z_col].diff()
    
    # --- Data Cleaning: Filter out 0-distance steps ---
    MIN_HORIZONTAL_STEP_M = 0.01 # 1 centimeter threshold
    df_cleaned = df[df['d_horizontal_m'] >= MIN_HORIZONTAL_STEP_M].copy()

    # Calculate the absolute slope (rise/run = dZ / d_horizontal)
    df_cleaned['Absolute_Slope'] = (df_cleaned['dZ_m'] / df_cleaned['d_horizontal_m']).abs()
    
    # --- Step 2: Calculate Slope Metrics (Mean, Median, Max) ---
    max_slope_value = df_cleaned['Absolute_Slope'].max()
    median_abs_slope = df_cleaned['Absolute_Slope'].median()
    mean_abs_slope = df_cleaned['Absolute_Slope'].mean()
    
    # --- Step 3: Obstacle Analysis (Mean, Median, Max Roughness) ---
    # We use the original 'df' for dZ_m to capture all vertical steps

    df_cleaned['dZ_m_abs'] = df_cleaned['dZ_m'].abs()
    max_vertical_step = df_cleaned['dZ_m_abs'].max()
    median_vertical_step = df_cleaned['dZ_m_abs'].median()
    mean_vertical_step = df_cleaned['dZ_m_abs'].mean()

    # --- Step 4: Compile and Format Results ---
    
    # Ensure all calculated metrics are treated as floats, handling potential NaNs safely
    max_slope_value = max_slope_value if not pd.isna(max_slope_value) else 0.0
    median_abs_slope = median_abs_slope if not pd.isna(median_abs_slope) else 0.0
    mean_abs_slope = mean_abs_slope if not pd.isna(mean_abs_slope) else 0.0
    
    max_vertical_step = max_vertical_step if not pd.isna(max_vertical_step) else 0.0
    median_vertical_step = median_vertical_step if not pd.isna(median_vertical_step) else 0.0
    mean_vertical_step = mean_vertical_step if not pd.isna(mean_vertical_step) else 0.0

    # Convert slope ratio (m/m) to standard engineering units
    max_grade_percent = max_slope_value * 100
    max_grade_angle = np.degrees(np.arctan(max_slope_value))
    median_grade_percent = median_abs_slope * 100
    mean_grade_percent = mean_abs_slope * 100
    
    results = {
        "File_Path": file_path,
        "Max_Slope_Ratio_m_m": max_slope_value,
        "Median_Absolute_Slope_m_m": median_abs_slope,
        "Mean_Absolute_Slope_m_m": mean_abs_slope,
        "Max_Grade_Percent": max_grade_percent,
        "Median_Grade_Percent": median_grade_percent,
        "Mean_Grade_Percent": mean_grade_percent,
        "Max_Grade_Angle_Degrees": max_grade_angle,
        "Max_Vertical_Step_m": max_vertical_step,
        "Median_Vertical_Step_m": median_vertical_step,
        "Mean_Vertical_Step_m": mean_vertical_step
    }

    # --- Step 5: Display and Export ---
    
    output_lines = [
        f"\n--- Final Engineering Metrics for Wheel Design ---",
        f"Data Anomalies Filtered (Horizontal Step < {MIN_HORIZONTAL_STEP_M}m): {len(df) - len(df_cleaned)} points",
        f"1. Slope (Grade) Metrics:",
        f"   - **MEAN Grade (Average):** {mean_grade_percent:.2f}% (Average expected load)",
        f"   - **ROBUST Grade (Median):** {median_grade_percent:.2f}% (Best for general power/efficiency - less sensitive to extremes)",
        f"   - **WORST-CASE Grade (Maximum):** {max_grade_percent:.2f}% (Critical check for maximum motor torque and grip)",
        f"2. Obstacle (Roughness) Metrics:",
        f"   - **MEAN Obstacle Height (Average):** {mean_vertical_step:.4f} meters (Informs general suspension dynamics)",
        f"   - **ROBUST Obstacle Height (Median):** {median_vertical_step:.4f} meters (Informs general suspension/ride compliance)",
        f"   - **WORST-CASE Obstacle Height (Maximum):** {max_vertical_step:.4f} meters (Critical safety check for **minimum required wheel diameter**)",
        f"-------------------------------------------------------"
    ]
    
    print("\n".join(output_lines))
    
    if output_filename:
        try:
            with open(output_filename, 'w') as f:
                f.write("\n".join(output_lines))
                f.write("\n\nRaw Metrics:\n")
                for key, value in results.items():
                    f.write(f"{key}: {value}\n")
            print(f"Success! Metrics have been safely exported to: {output_filename}")
        except Exception as e:
            print(f"WARNING: Could not write the output file '{output_filename}'. Error details: {e}")

    return results