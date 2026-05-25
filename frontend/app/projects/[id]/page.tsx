import { redirect } from "next/navigation";

export default function ProjectRedirect({ params }: { params: { id: string } }) {
  redirect(`/projects/${params.id}/workspace`);
}