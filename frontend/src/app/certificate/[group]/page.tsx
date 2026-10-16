import Link from "next/link";
import { notFound } from "next/navigation";
import { auth } from "@/auth";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { PrintButton } from "@/components/certificate/print-button";
import { fetchCertificatesServerSide, sessionToken } from "@/lib/server-progress";

export default async function CertificatePage({ params }: { params: Promise<{ group: string }> }) {
  const { group } = await params;
  const token = await sessionToken();
  if (!token) {
    return (
      <Alert>
        <AlertTitle>Sign in to view this certificate</AlertTitle>
      </Alert>
    );
  }

  const certificates = await fetchCertificatesServerSide();
  const cert = certificates?.[group];
  if (!cert) notFound();

  if (!cert.unlocked) {
    return (
      <Alert>
        <AlertTitle>Not unlocked yet</AlertTitle>
        <AlertDescription className="space-y-3">
          <p>
            {cert.completed} / {cert.total} nodes completed for {cert.label}. Finish every node in this track to
            unlock its certificate.
          </p>
          <Link href="/profile" className={buttonVariants({ variant: "outline" })}>
            Back to profile
          </Link>
        </AlertDescription>
      </Alert>
    );
  }

  const session = await auth();
  const recipientName = session?.user?.name ?? session?.user?.email ?? "Learndata Learner";
  const today = new Date().toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });

  return (
    <div className="space-y-6 print:space-y-0">
      <div className="flex justify-end gap-2 print:hidden">
        <Link href="/profile" className={buttonVariants({ variant: "outline" })}>
          Back to profile
        </Link>
        <PrintButton />
      </div>

      <div className="mx-auto max-w-3xl animate-in zoom-in-95 fade-in rounded-lg border-4 border-double border-primary/60 bg-card p-16 text-center shadow-sm duration-700 print:animate-none">
        <p className="text-sm uppercase tracking-[0.3em] text-muted-foreground">Certificate of Completion</p>
        <h1 className="mt-6 text-4xl font-semibold tracking-tight">{cert.label}</h1>
        <p className="mt-8 text-lg text-muted-foreground">This certifies that</p>
        <p className="mt-2 text-3xl font-semibold">{recipientName}</p>
        <p className="mt-8 text-muted-foreground">
          has completed every lesson and capstone in the {cert.label} track on Learndata.
        </p>
        <p className="mt-10 text-sm text-muted-foreground">{today}</p>
      </div>
    </div>
  );
}
