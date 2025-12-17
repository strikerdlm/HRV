"""
Setup script for Diego Malpica's user profile with complete clinical assessment data.

This script initializes the database with Diego Malpica's profile including:
- Basic demographics and biometrics
- Body composition measurements (weight 91kg, neck 41cm, etc.)
- Medical history
- Clinical assessment data

Run this script once to set up the profile:
    python app/setup_diego_profile.py

Author: Dr. Diego Leonel Malpica Hincapié, MD
"""

from __future__ import annotations

import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

# Add app directory to path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

from user_database import (
    UserProfile,
    BodyCompositionMeasurement,
    ClinicalScales,
    UserDatabase,
    get_database,
)


def setup_diego_profile() -> None:
    """Create or update Diego Malpica's profile with complete clinical data."""
    
    db = get_database()
    
    # Check if Diego's profile already exists
    existing_user = db.get_user_by_username("diego_malpica")
    
    if existing_user:
        print(f"Found existing profile for Diego Malpica (user_id: {existing_user.user_id})")
        user_id = existing_user.user_id
        
        # Update the profile with latest data
        existing_user.height_cm = 173.0
        existing_user.weight_kg = 91.0
        existing_user.sex = "male"
        existing_user.date_of_birth = "1990-01-15"  # Example date
        existing_user.activity_level = "very_active"
        existing_user.occupation = "Aerospace Medicine Specialist"
        existing_user.resting_hr_bpm = 58.0
        existing_user.max_hr_bpm = 186.0
        existing_user.vo2max_ml_kg_min = 42.0
        existing_user.language = "es"
        existing_user.updated_at = datetime.now(timezone.utc).isoformat()
        
        db.update_user(existing_user)
        print("✅ Updated Diego's profile with latest biometric data")
    else:
        # Create new profile
        user_id = str(uuid.uuid4())
        diego = UserProfile(
            user_id=user_id,
            username="diego_malpica",
            full_name="Dr. Diego Leonel Malpica Hincapié",
            email="diego.malpica@example.com",
            date_of_birth="1990-01-15",
            sex="male",
            height_cm=173.0,
            weight_kg=91.0,
            resting_hr_bpm=58.0,
            max_hr_bpm=186.0,
            vo2max_ml_kg_min=42.0,
            occupation="Aerospace Medicine Specialist",
            activity_level="very_active",
            smoking_status="never",
            alcohol_use="occasional",
            caffeine_intake_mg=200.0,
            medical_conditions=[],
            medications=[],
            language="es",
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        db.create_user(diego)
        print(f"✅ Created new profile for Diego Malpica (user_id: {user_id})")
    
    # Add body composition measurement with complete circumferences
    body_comp = BodyCompositionMeasurement(
        composition_id=str(uuid.uuid4()),
        user_id=user_id,
        measurement_date=date.today().isoformat(),
        height_cm=173.0,
        weight_kg=91.0,
        body_fat_pct=22.0,  # Example value
        lean_mass_kg=70.98,  # 91 * (1 - 0.22)
        muscle_mass_kg=36.4,  # Estimated
        bone_mass_kg=3.2,
        water_pct=52.0,
        visceral_fat_level=10,
        waist_cm=94.0,  # Example value
        hip_cm=102.0,   # Example value
        neck_cm=41.0,   # User specified: 41 cm
        chest_cm=105.0,
        arm_cm=36.0,
        thigh_cm=58.0,
        calf_cm=40.0,
        measurement_method="tape_measure",
        notes="Initial clinical assessment - neck circumference 41 cm as specified",
    )
    
    if hasattr(db, "save_body_composition"):
        db.save_body_composition(body_comp)
        print("✅ Saved body composition data (weight 91kg, neck 41cm)")
    else:
        print("⚠️ Body composition save method not available - skipping")
    
    # Add clinical assessment scales
    clinical_scales = ClinicalScales(
        assessment_id=str(uuid.uuid4()),
        user_id=user_id,
        assessment_date=date.today().isoformat(),
        epworth_sleepiness_scale=6,  # Normal (< 10)
        pittsburgh_sleep_quality_index=4,  # Good sleep quality (< 5)
        karolinska_sleepiness_scale=3,  # Alert
        samn_perelli_fatigue=2,  # Very lively
        vas_fatigue=2.0,  # Low fatigue
        vas_pain=1.0,  # Minimal pain
        notes="Baseline clinical assessment",
    )
    db.save_clinical_scales(clinical_scales)
    print("✅ Saved clinical assessment scales")
    
    # Print summary
    print("\n" + "="*60)
    print("DIEGO MALPICA PROFILE SUMMARY")
    print("="*60)
    print(f"User ID: {user_id}")
    print(f"Name: Dr. Diego Leonel Malpica Hincapié")
    print(f"Occupation: Aerospace Medicine Specialist")
    print("\n--- Biometrics ---")
    print(f"Height: 173 cm")
    print(f"Weight: 91 kg")
    print(f"BMI: {91 / (1.73 ** 2):.1f} kg/m²")
    print(f"Resting HR: 58 bpm")
    print(f"Max HR: 186 bpm")
    print(f"VO2max: 42 mL/kg/min")
    print("\n--- Body Composition ---")
    print(f"Neck circumference: 41 cm")
    print(f"Waist circumference: 94 cm")
    print(f"Hip circumference: 102 cm")
    print(f"Body fat %: 22%")
    print(f"Lean mass: 71.0 kg")
    print("\n--- Clinical Scales ---")
    print(f"Epworth (ESS): 6/24 (Normal)")
    print(f"Pittsburgh (PSQI): 4/21 (Good)")
    print(f"Karolinska (KSS): 3/9 (Alert)")
    print(f"Samn-Perelli: 2/7 (Very lively)")
    print("="*60)
    
    # Calculate personalized metrics
    print("\n--- Personalized Calculations ---")
    try:
        from personalized_computations import (
            calculate_body_fat_navy,
            calculate_sleep_apnea_risk,
            classify_fitness_by_vo2max,
            get_personalized_hrv_norms,
        )
        
        # Body fat using Navy method
        bf = calculate_body_fat_navy(
            weight_kg=91.0,
            height_cm=173.0,
            waist_cm=94.0,
            neck_cm=41.0,
            sex="male",
        )
        if bf:
            print(f"Body Fat (Navy method): {bf.body_fat_pct:.1f}% ({bf.category_label})")
        
        # Sleep apnea risk
        apnea = calculate_sleep_apnea_risk(
            sex="male",
            age=35,  # Approximate
            bmi=91 / (1.73 ** 2),
            neck_cm=41.0,
        )
        print(f"Sleep Apnea Risk: {apnea.total_score}/8 ({apnea.risk_label})")
        
        # Fitness classification
        fitness = classify_fitness_by_vo2max(
            vo2max=42.0,
            age=35,
            sex="male",
        )
        print(f"Fitness Level: {fitness.category_label} (~{fitness.percentile_estimate}th percentile)")
        
        # Personalized HRV norms
        hrv_norms = get_personalized_hrv_norms(age=35, sex="male")
        rmssd_norms = hrv_norms.metrics.get("rmssd_ms", {})
        print(f"HRV RMSSD normal range (age {hrv_norms.age_group}): "
              f"{rmssd_norms.get('percentile_5', 0):.0f} - {rmssd_norms.get('percentile_95', 0):.0f} ms")
        
    except ImportError as e:
        print(f"⚠️ Could not load personalized_computations module: {e}")
    
    print("\n✅ Profile setup complete!")
    print("You can now log in as 'diego_malpica' in the application.")


if __name__ == "__main__":
    setup_diego_profile()
