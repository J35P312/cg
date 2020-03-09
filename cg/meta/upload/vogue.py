"""API to run Vogue"""
# -*- coding: utf-8 -*-
import json

from cg.apps.gt import GenotypeAPI
from cg.apps.vogue import VogueAPI
from cg.apps.lims import LimsAPI
from cg.store import Store


class UploadVogueAPI:
    """API to load data into Vogue"""

    def __init__(
        self, genotype_api: GenotypeAPI, vogue_api: VogueAPI, store: Store, lims_api: LimsAPI
    ):
        self.genotype_api = genotype_api
        self.vogue_api = vogue_api
        self.store = store
        self.lims_api = lims_api

    def load_genotype(self, days):
        """Loading genotype data from the genotype database into the trending database"""
        samples = self.genotype_api.export_sample(days=days)
        samples = json.loads(samples)
        for sample_id, sample_dict in samples.items():
            sample_dict["_id"] = sample_id
            self.vogue_api.load_genotype_data(sample_dict)

        samples_analysis = self.genotype_api.export_sample_analysis(days=days)
        samples_analysis = json.loads(samples_analysis)
        for sample_id, sample_dict in samples_analysis.items():
            sample_dict["_id"] = sample_id
            self.vogue_api.load_genotype_data(sample_dict)

    def load_apptags(self):
        """Loading application tags from statusdb into the trending database"""
        apptags = self.store.applications()
        apptags_for_vogue = []
        for tag in apptags.all():
            apptags_for_vogue.append(
                {"tag": tag.tag, "prep_category": tag.prep_category}
            )

        self.vogue_api.load_apptags(apptags_for_vogue)

    def load_samples(self, days):
        """Loading samples from lims into the trending database"""
        samples_for_vogue = self.build_sample()
        self.vogue_api.load_samples(samples_for_vogue)

    def load_flowcells(self, days):
        """Loading flowcells from lims into the trending database"""

        self.vogue_api.load_flowcells(days=days)


    def build_sample(self, sample: Sample, lims: Lims, adapter)-> dict:
        """Parse lims sample"""
        application_tag = sample.udf.get('Sequencing Analysis')
        category = adapter.get_category(application_tag) 
        
        mongo_sample = {'_id' : sample.id}
        mongo_sample['family'] = sample.udf.get('Family')
        mongo_sample['strain'] = sample.udf.get('Strain')
        mongo_sample['source'] = sample.udf.get('Source')
        mongo_sample['customer'] = sample.udf.get('customer')
        mongo_sample['priority'] = sample.udf.get('priority')
        mongo_sample['initial_qc'] = sample.udf.get('Passed Initial QC')
        mongo_sample['library_qc'] = sample.udf.get('Passed Library QC')
        mongo_sample['sequencing_qc'] = sample.udf.get('Passed Sequencing QC')
        mongo_sample['application_tag'] = application_tag
        mongo_sample['category'] = category

        conc_and_amount = get_final_conc_and_amount_dna(application_tag, sample.id, lims)
        mongo_sample['amount'] = conc_and_amount.get('amount')
        mongo_sample['amount-concentration'] = conc_and_amount.get('concentration')

        concentration_and_nr_defrosts = get_concentration_and_nr_defrosts(application_tag, sample.id, lims)
        mongo_sample['nr_defrosts'] = concentration_and_nr_defrosts.get('nr_defrosts')
        mongo_sample['nr_defrosts-concentration'] = concentration_and_nr_defrosts.get('concentration')
        mongo_sample['lotnr'] = concentration_and_nr_defrosts.get('lotnr')

        sequenced_at = get_sequenced_date(sample, lims)
        received_at = get_received_date(sample, lims)
        prepared_at = get_prepared_date(sample, lims)
        delivered_at = get_delivery_date(sample, lims)

        mongo_sample['sequenced_date'] = sequenced_at
        mongo_sample['received_date'] = received_at
        mongo_sample['prepared_date'] = prepared_at
        mongo_sample['delivery_date'] = delivered_at
        mongo_sample['sequenced_to_delivered'] = get_number_of_days(sequenced_at, delivered_at)
        mongo_sample['prepped_to_sequenced'] = get_number_of_days(prepared_at, sequenced_at)
        mongo_sample['received_to_prepped'] = get_number_of_days(received_at, prepared_at)
        mongo_sample['received_to_delivered'] = get_number_of_days(received_at, delivered_at)

        mongo_sample['microbial_library_concentration'] = get_microbial_library_concentration(application_tag, sample.id, lims)
        
        mongo_sample['library_size_pre_hyb'] = get_library_size(application_tag, sample.id, lims, 
                                                                'TWIST', 'library_size_pre_hyb')
        mongo_sample['library_size_post_hyb'] = get_library_size(application_tag, sample.id, lims, 
                                                                'TWIST', 'library_size_post_hyb')
        if not mongo_sample['library_size_post_hyb']:
            if not received_at or received_at < dt(2019, 1, 1):
                mongo_sample['library_size_pre_hyb'] = get_library_size(application_tag, sample.id, lims, 
                                                                    'SureSelect', 'library_size_pre_hyb')
                mongo_sample['library_size_post_hyb'] = get_library_size(application_tag, sample.id, lims, 
                                                                    'SureSelect', 'library_size_post_hyb')

        for key in list(mongo_sample.keys()):
            if mongo_sample[key] is None:
                mongo_sample.pop(key)

        return mongo_sample