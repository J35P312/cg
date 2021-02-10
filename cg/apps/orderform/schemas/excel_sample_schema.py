from typing import List, Optional

from cg.apps.lims.orderform import REV_SEX_MAP, SOURCE_TYPES
from cg.apps.orderform.schemas.orderform_schema import OrderSample
from pydantic import Field, validator


class ExcelSample(OrderSample):
    application: str = Field(..., alias="UDF/Sequencing Analysis")
    capture_kit: str = Field(None, alias="UDF/Capture Library version")
    case_id: str = Field(None, alias="UDF/familyID")
    comment: str = Field(None, alias="UDF/Comment")
    concentration: str = Field(None, alias="UDF/Concentration (nM)")
    concentration_sample: str = Field(None, alias="UDF/Sample Conc.")
    container: str = Field(None, alias="Container/Type")
    container_name: str = Field(None, alias="Container/Name")
    custom_index: str = Field(None, alias="UDF/Custom index")
    customer: str = Field(..., alias="UDF/customer")
    data_analysis: str = Field(..., alias="UDF/Data Analysis")
    data_delivery: str = Field(None, alias="UDF/Data Delivery")
    elution_buffer: str = Field(None, alias="UDF/Sample Buffer")
    extraction_method: str = Field(None, alias="UDF/Extraction method")
    father: str = Field(None, alias="UDF/fatherID")
    formalin_fixation_time: str = Field(None, alias="UDF/Formalin Fixation Time")
    from_sample: str = Field(None, alias="UDF/is_for_sample")
    index: str = Field(None, alias="UDF/Index type")
    index_number: str = Field(None, alias="UDF/Index number")
    mother: str = Field(None, alias="UDF/motherID")
    name: str = Field(..., alias="Sample/Name")
    organism: str = Field(None, alias="UDF/Strain")
    organism_other: str = Field(None, alias="UDF/Other species")
    panels: List[str] = Field(None, alias="UDF/Gene List")
    pool: str = Field(None, alias="UDF/pool name")
    post_formalin_fixation_time: str = Field(None, alias="UDF/Post Formalin Fixation Time")
    priority: str = Field(None, alias="UDF/priority")
    quantity: str = Field(None, alias="UDF/Quantity")
    reagent_label: str = Field(None, alias="Sample/Reagent Label")
    reference_genome: str = Field(None, alias="UDF/Reference Genome Microbial")
    require_qcok: bool = Field(None, alias="UDF/Process only if QC OK")
    rml_plate_name: str = Field(None, alias="UDF/RML plate name")
    sex: str = Field(None, alias="UDF/Gender")
    source: str = Field(None, alias="UDF/Source")
    status: str = Field(None, alias="UDF/Status")
    time_point: str = Field(None, alias="UDF/time_point")
    tissue_block_size: str = Field(None, alias="UDF/Tissue Block Size")
    tumour: bool = Field(None, alias="UDF/tumor")
    tumour_purity: str = Field(None, alias="UDF/tumour purity")
    volume: str = Field(None, alias="UDF/Volume (uL)")
    well_position: str = Field(None, alias="Sample/Well Location")
    well_position_rml: str = Field(None, alias="UDF/RML well position")

    @validator("data_analysis")
    def validate_pipeline(cls, value):
        if not value:
            return None
        if value.lower() == "no analysis":
            return value
        return value.lower()

    @validator(
        "index_number", "volume", "quantity", "concentration", "concentration_sample", "time_point"
    )
    def numeric_value(cls, value: Optional[str]):
        if not value:
            return None
        str_value = value.rsplit(".0")[0]
        if str_value.replace(".", "").isnumeric():
            return str_value
        raise AttributeError(f"Non numeric value {value}")

    @validator("mother", "father")
    def validate_parent(cls, value: str):
        if value == "0.0":
            return None
        return value

    @validator("source")
    def validate_source(cls, value: Optional[str]):
        if value not in SOURCE_TYPES:
            raise ValueError(f"{value} is not a valid source")
        return value

    @validator("sex")
    def convert_sex(cls, value: Optional[str]):
        if not value:
            return None
        value = value.strip()
        return REV_SEX_MAP.get(value, "unknown")

    @validator("panels", pre=True)
    def parse_panels(cls, value):
        if not value:
            return None
        separator = ";"
        if ":" in value:
            separator = ":"
        return value.split(separator)

    @validator("priority", "status")
    def convert_to_lower(cls, value: Optional[str]):
        if not value:
            return None
        value = value.lower()
        if value == "förtur":
            return "priority"
        return value
