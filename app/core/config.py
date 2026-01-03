from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional, List


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env", extra="ignore"  # Ignore extra fields in .env
    )

    database_url: str
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "bacopilot_db"
    db_user: str = "postgres"
    db_password: str

    sendgrid_api_key: Optional[str] = None
    sendgrid_from_email: Optional[str] = None

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    environment: str = "development"
    debug: bool = True

    host: str = "0.0.0.0"
    port: int = 8010

    frontend_url: Optional[List[str]] = None

    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    ai_service_url_srs: str
    ai_service_url_wireframe: str
    ai_service_url_diagram_usecase: str
    ai_service_url_diagram_class: str
    ai_service_url_diagram_activity: str
    ai_service_url_stakeholder_register: str
    ai_service_url_high_level_requirements: str
    ai_service_url_requirements_management_plan: str
    ai_service_url_business_case: str
    ai_service_url_scope_statement: str
    ai_service_url_product_roadmap: str

    ai_service_url_hld_arch: str
    ai_service_url_hld_cloud: str
    ai_service_url_hld_tech: str

    ai_service_url_lld_arch: str
    ai_service_url_lld_db: str
    ai_service_url_lld_api: str
    ai_service_url_lld_pseudo: str

    ai_service_url_uiux_wireframe: str
    ai_service_url_uiux_mockup: str
    ai_service_url_uiux_prototype: str

    ai_service_url_feasibility_study: str
    ai_service_url_cost_benefit_analysis: str
    ai_service_url_risk_register: str
    ai_service_url_compliance: str
    
    # Metadata extraction service
    ai_service_url_metadata_extraction: str = "http://ai:8000/api/v1/metadata/extract"

settings = Settings()
