export interface ExclusionEntry {
  source_id: string;
  category: string;
  reason: string;
}

export interface DatasetInfo {
  total_source: number;
  total_selected: number;
  total_included: number;
  total_excluded: number;
  exclusions: ExclusionEntry[];
}
