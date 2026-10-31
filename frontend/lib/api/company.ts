import { apiFetch, shouldUseMocks } from "@/lib/api/client";
import type { CompanyProfile } from "@/lib/api/types";
import { mockCompany } from "@/lib/mocks/data";

export async function getCompanyProfile(): Promise<CompanyProfile> {
  if (shouldUseMocks()) {
    return mockCompany;
  }
  return apiFetch<CompanyProfile>("/company");
}
