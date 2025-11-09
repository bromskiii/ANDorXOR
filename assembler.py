# w.py (FIXED)

# --- Configuration ---

# --- Imports ---
from get_topography import analyze_and_export_metrics 
from terrain_identifier import get_terrain_classification
from typing import Dict, Any, List, Optional
import json # Used for displaying the final structure

# FIX 1: Renamed the function below the main execution block to match the one being imported.
# FIX 2: Removed the 'include_raw' argument from the function signature.
def combine_analysis_to_json(db_path: str, image_path: str, pretty: bool = False) -> str:
    """
    Executes the full terrain analysis workflow (quantitative and qualitative),
    returns the data structure as a JSON string for use by the decision-making AI.
    
    Args:
        db_path (str): Path to the elevation data Excel file.
        image_path (str): Path to the terrain image for classification.
        pretty (bool): Whether to format the JSON output with indentation.

    Returns:
        str: A JSON string containing all design metrics.
    """
    
    print("--- Starting Full Design Data Extraction ---")

    # 1. QUANTITATIVE ANALYSIS (From Elevation Data)
    quantitative_metrics = analyze_and_export_metrics(
        file_path=db_path, 
        output_filename=None 
    )

    if not quantitative_metrics:
        print("Analysis failed: Quantitative metrics could not be loaded or calculated.")
        # Return an empty dict string so the AA script doesn't completely fail
        return json.dumps({"analysis": {"error": "Quantitative metrics failed"}})

    # 2. QUALITATIVE ANALYSIS (From Image)
    terrain_classification_results: List[Dict[str, Any]] = []
    try:
        results = get_terrain_classification(image_path)
        terrain_classification_results = [{'label': item['label'], 'score': item['score']} for item in results]
    except Exception as e:
        print(f"\nERROR: Could not run image classification. Details: {e}")
    
    # 3. DERIVE KEY DESIGN PARAMETERS
    median_obstacle = quantitative_metrics['Median_Vertical_Step_m']
    max_obstacle = quantitative_metrics['Max_Vertical_Step_m']
    median_grade_percent = quantitative_metrics['Median_Grade_Percent']
    mean_grade_percent = quantitative_metrics['Mean_Grade_Percent']
    
    top_terrain = terrain_classification_results[0]['label'] if terrain_classification_results else "unknown"

    robust_wheel_diameter = median_obstacle * 2.0 
    max_safety_wheel_diameter = max_obstacle * 2.0 

    tire_tread_suggestion = "All-Terrain Tread"
    if "marshy" in top_terrain or "sandy" in top_terrain:
        tire_tread_suggestion = "Deep, Aggressive Tread (Low Ground Pressure)"
    elif "rocky" in top_terrain:
        tire_tread_suggestion = "Tough, Puncture-Resistant Tread (Durability)"

    # 4. UNIFY AND RETURN ALL DATA
    final_data = {
        "quantitative_metrics": {
            "mean_grade_percent": mean_grade_percent,
            "median_grade_percent": median_grade_percent,
            "max_grade_percent": quantitative_metrics['Max_Grade_Percent'],
            "max_grade_angle_degrees": quantitative_metrics['Max_Grade_Angle_Degrees'],
            "mean_absolute_slope_m_m": quantitative_metrics['Mean_Absolute_Slope_m_m'],
            "median_absolute_slope_m_m": quantitative_metrics['Median_Absolute_Slope_m_m'],
            "max_slope_ratio_m_m": quantitative_metrics['Max_Slope_Ratio_m_m'],
            
            "mean_vertical_step_m": quantitative_metrics['Mean_Vertical_Step_m'],
            "median_vertical_step_m": median_obstacle,
            "max_vertical_step_m": max_obstacle,
        },
        "qualitative_metrics_full": terrain_classification_results,
        "design_recommendations": {
            "robust_wheel_diameter_m": robust_wheel_diameter,
            "power_sizing_typical_grade_percent_mean": mean_grade_percent,
            "power_sizing_robust_grade_percent_median": median_grade_percent,
            "max_safety_check_grade_percent": quantitative_metrics['Max_Grade_Percent'],
            "max_safety_check_wheel_diameter_m": max_safety_wheel_diameter,
            "primary_terrain_type": top_terrain,
            "tire_tread_suggestion": tire_tread_suggestion,
        }
    }
    
    print("\n--- Design Data Successfully Compiled ---")
    
    # Return as JSON string
    return json.dumps(final_data, indent=4 if pretty else None)
