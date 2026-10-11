import { apiFetch, useMocks } from "@/lib/api/client";
import type { CompanyProfile } from "@/lib/api/types";
import { mockCompany } from "@/lib/mocks/data";

export async function getCompanyProfile(): Promise<CompanyProfile> {
  if (useMocks()) {
    return mockCompany;
  }
  return apiFetch<CompanyProfile>("/company");
}
