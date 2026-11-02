import { cookies } from "next/headers";
import { notFound } from "next/navigation";

import { getApiInternalUrl } from "@/lib/api";
import { getServerLocale } from "@/lib/serverLocale";

import { AdminDashboard } from "./AdminDashboard";

export const dynamic = "force-dynamic";

/** True only when the api answers the smallest section: it alone decides who is an admin. */
async function isAdmin(): Promise<boolean> {
  const jar = await cookies();
  const cookie = jar
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");
  try {
    const response = await fetch(`${getApiInternalUrl()}/admin/units`, {
      method: "GET",
      headers: { Accept: "application/json", ...(cookie ? { Cookie: cookie } : {}) },
      cache: "no-store",
    });
    return response.ok;
  } catch {
    return false;
  }
}

/** The read-only dashboard (spec 055 US4). Anyone else gets the app's not-found page. */
export default async function AdminPage() {
  if (!(await isAdmin())) notFound();
  return <AdminDashboard locale={await getServerLocale()} />;
}
