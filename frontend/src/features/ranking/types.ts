export interface CandidateRanking {
  candidate_id: string;
  rank: number;
  category: string;
  matched_requirements: string[];
  missing_requirements: string[];
  evidence: string;
}

export interface ShortlistResponse {
  rankings: CandidateRanking[];
}

export interface ApiError {
  error_code: 'invalid_jd' | 'injection_detected' | 'ranking_failed';
  message: string;
}

export type OverrideStatus = 'shortlisted' | 'rejected';

// Absent key = no override applied. Never store null values.
export type OverrideMap = Record<string, OverrideStatus>;
