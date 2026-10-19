/**
 * Health check proxy route.
 * Optional: provides /health endpoint for load balancers.
 */
export async function GET() {
  return Response.json(
    {
      status: 'healthy',
      timestamp: new Date().toISOString(),
    },
    { status: 200 }
  )
}

