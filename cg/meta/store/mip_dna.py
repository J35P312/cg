"""Builds MIP DNA bundle for linking in Housekeeper"""


def build_bundle(config_data: dict, sampleinfo_data: dict) -> dict:
    """Create a new bundle."""
    data = {
        'name': config_data['case'],
        'created': sampleinfo_data['date'],
        'pipeline_version': sampleinfo_data['version'],
        'files': get_files(config_data, sampleinfo_data),
    }
    return data


def get_files(config_data: dict, sampleinfo_data: dict) -> dict:
    """Get all the files from the MIP files."""

    data = [{
        'path': config_data['config_path'],
        'tags': ['mip-config'],
        'archive': True,
    }, {
        'path': config_data['sampleinfo_path'],
        'tags': ['sampleinfo'],
        'archive': True,
    }, {
        'path': sampleinfo_data['pedigree_path'],
        'tags': ['pedigree'],
        'archive': False,
    }, {
        'path': config_data['log_path'],
        'tags': ['mip-log'],
        'archive': True,
    }, {
        'path': sampleinfo_data['qcmetrics_path'],
        'tags': ['qcmetrics'],
        'archive': True,
    }, {
        'path': sampleinfo_data['snv']['bcf'],
        'tags': ['snv-bcf', 'snv-gbcf'],
        'archive': True,
    }, {
        'path': f"{sampleinfo_data['snv']['bcf']}.csi",
        'tags': ['snv-bcf-index', 'snv-gbcf-index'],
        'archive': True,
    }, {
        'path': sampleinfo_data['sv']['bcf'],
        'tags': ['sv-bcf'],
        'archive': True,
    }, {
        'path': f"{sampleinfo_data['sv']['bcf']}.csi",
        'tags': ['sv-bcf-index'],
        'archive': True,
    }, {
        'path': sampleinfo_data['peddy']['ped_check'],
        'tags': ['peddy', 'ped-check'],
        'archive': False,
    }, {
        'path': sampleinfo_data['peddy']['ped'],
        'tags': ['peddy', 'ped'],
        'archive': False,
    }, {
        'path': sampleinfo_data['peddy']['sex_check'],
        'tags': ['peddy', 'sex-check'],
        'archive': False,
    }]

    # this key exists only for wgs
    if sampleinfo_data['str_vcf']:
        data.append({
            'path': sampleinfo_data['str_vcf'],
            'tags': ['vcf-str'],
            'archive': True
        })

    for variant_type in ['snv', 'sv']:
        for output_type in ['clinical', 'research']:
            vcf_path = sampleinfo_data[variant_type][f"{output_type}_vcf"]
            if vcf_path is None:
                LOG.warning(f"missing file: {output_type} {variant_type} VCF")
                continue
            vcf_tag = f"vcf-{variant_type}-{output_type}"
            data.append({
                'path': vcf_path,
                'tags': [vcf_tag],
                'archive': True,
            })
            data.append({
                'path': f"{vcf_path}.tbi" if variant_type == 'snv' else f"{vcf_path}.csi",
                'tags': [f"{vcf_tag}-index"],
                'archive': True,
            })

    for sample_data in sampleinfo_data['samples']:
        data.append({
            'path': sample_data['sambamba'],
            'tags': ['coverage', sample_data['id']],
            'archive': False,
        })

        # Bam pre-processing
        bam_path = sample_data['bam']
        bai_path = f"{bam_path}.bai"
        if not Path(bai_path).exists():
            bai_path = bam_path.replace('.bam', '.bai')

        data.append({
            'path': bam_path,
            'tags': ['bam', sample_data['id']],
            'archive': False,
        })
        data.append({
            'path': bai_path,
            'tags': ['bam-index', sample_data['id']],
            'archive': False,
        })

        # Only for wgs data
        # Downsamples MT bam pre-processing
        if sample_data['subsample_mt']:
            mt_bam_path = sample_data['subsample_mt']
            mt_bai_path = f"{mt_bam_path}.bai"
            if not Path(mt_bai_path).exists():
                mt_bai_path = mt_bam_path.replace('.bam', '.bai')
            data.append({
                'path': mt_bam_path,
                'tags': ['bam-mt', sample_data['id']],
                'archive': False,
            })
            data.append({
                'path': mt_bai_path,
                'tags': ['bam-mt-index', sample_data['id']],
                'archive': False,
            })

        cytosure_path = sample_data['vcf2cytosure']
        data.append({
            'path': cytosure_path,
            'tags': ['vcf2cytosure', sample_data['id']],
            'archive': False,
        })

    return data
